import io

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import health_record, prescription_ocr, lab_ocr


class FakeBed:
    def __init__(self, case_id=1, length=10, encounter_length=10, vitals=None):
        self.case_id = case_id
        self.length = length
        self.encounter_length = encounter_length
        self.vitals = vitals or {}
        self.waveform_loaded = False

    def tick(self, t):
        return dict(self.vitals)


def identity(n=1, **kw):
    d = {
        "bed_id": f"Bed-{n}", "case_id": n, "name": f"Name {n}", "abha_id": f"ABHA-{n}",
        "age": 30, "sex": "M", "department": "General surgery", "procedure": "Proc", "diagnosis": "Dx",
        "asa_class": 1, "disclaimer": "d",
    }
    d.update(kw)
    return d


@pytest.fixture
def env(db, monkeypatch):
    beds = {"Bed-A": FakeBed(case_id=11), "Bed-DEMO": FakeBed(case_id=12, encounter_length=40)}
    idents = {"Bed-A": identity(1), "Bed-DEMO": identity(2, is_demo=True)}
    monkeypatch.setattr(main, "beds", beds)
    monkeypatch.setattr(main, "bed_identities", idents)
    monkeypatch.setattr(main, "sim_t", 100)
    return main


@pytest.fixture
def client(env):
    return TestClient(main.app)  # no ``with``: startup hooks are tested separately


def png():
    from PIL import Image

    b = io.BytesIO()
    Image.new("RGB", (4, 4)).save(b, format="PNG")
    return b.getvalue()


def test_health_and_beds_listing(client):
    assert client.get("/api/health").json() == {"status": "ok", "beds_loaded": 2}
    beds = {b["bed_id"]: b for b in client.get("/api/beds").json()}
    assert beds["Bed-A"] == {
        "bed_id": "Bed-A", "source": "VitalDB case #11", "length_sec": 10, "encounter_length_sec": 10, "is_demo": False,
    }
    assert beds["Bed-DEMO"]["is_demo"] is True and beds["Bed-DEMO"]["encounter_length_sec"] == 40


def test_beds_listing_tolerates_missing_identity(client, env, monkeypatch):
    monkeypatch.setattr(main, "bed_identities", {})
    assert all(b["is_demo"] is False for b in client.get("/api/beds").json())


UNKNOWN_BED_ROUTES = [
    ("get", "/api/beds/nope/identity"),
    ("get", "/api/beds/nope/insurance"),
    ("get", "/api/beds/nope/prescriptions"),
    ("get", "/api/beds/nope/prescriptions/pending"),
    ("get", "/api/beds/nope/labs/pending"),
    ("get", "/api/beds/nope/labs"),
    ("get", "/api/beds/nope/discharge-summary"),
    ("get", "/api/beds/nope/discharge-summary.html"),
    ("get", "/api/beds/nope/record"),
    ("post", "/api/beds/nope/prescriptions/pending/x/approve"),
    ("post", "/api/beds/nope/prescriptions/pending/x/reject"),
    ("post", "/api/beds/nope/labs/pending/x/approve"),
    ("post", "/api/beds/nope/labs/pending/x/reject"),
]


@pytest.mark.parametrize("method,url", UNKNOWN_BED_ROUTES)
def test_unknown_bed_is_404(client, method, url):
    r = getattr(client, method)(url)
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown bed_id"


@pytest.mark.parametrize("url", ["/api/beds/nope/prescriptions/ocr", "/api/beds/nope/labs/ocr"])
def test_unknown_bed_ocr_upload_404(client, url):
    r = client.post(url, files={"file": ("x.png", png(), "image/png")})
    assert r.status_code == 404


def test_identity_endpoint(client):
    assert client.get("/api/beds/Bed-A/identity").json()["abha_id"] == "ABHA-1"


def test_insurance_endpoint_hides_private_counters(client, db):
    r = client.get("/api/beds/Bed-A/insurance").json()
    assert set(r) == {"disclaimer", "abha_id"}  # no record yet
    db.upsert_insurance_eligibility("ABHA-1", "Ins", "POL", "eligible", "AUTH", 3)
    r = client.get("/api/beds/Bed-A/insurance").json()
    assert r["insurer"] == "Ins" and r["abha_id"] == "ABHA-1"
    assert not any(k.startswith("_") for k in r)
    assert r["last_claim"] is None


def test_prescriptions_listing(client, db):
    db.insert_prescriptions("Bed-A", [dict(drug="d", dose="1", route="IV", frequency_sim_sec=5, status="active", next_due=None)])
    r = client.get("/api/beds/Bed-A/prescriptions").json()
    assert [o["drug"] for o in r["orders"]] == ["d"]
    assert "Synthetic" in r["disclaimer"]


# ---------------- prescription OCR flow ----------------

def upload_rx(client, monkeypatch, text, bed="Bed-A"):
    monkeypatch.setattr(prescription_ocr.pytesseract, "image_to_string", lambda im: text)
    return client.post(f"/api/beds/{bed}/prescriptions/ocr", files={"file": ("rx.png", png(), "image/png")})


def test_prescription_ocr_creates_pending_candidates_and_event(client, monkeypatch, db):
    r = upload_rx(client, monkeypatch, "Paracetamol 500mg PO BD\nAmoxicillin 250 mg TDS\n")
    assert r.status_code == 200
    body = r.json()
    assert [c["drug"] for c in body["candidates"]] == ["Paracetamol", "Amoxicillin"]
    ids = [c["id"] for c in body["candidates"]]
    assert len(set(ids)) == 2 and all(len(i) == 8 for i in ids)
    assert body["raw_text"].startswith("Paracetamol")
    pending = client.get("/api/beds/Bed-A/prescriptions/pending").json()["candidates"]
    assert [p["id"] for p in pending] == ids
    (ev,) = health_record.get_timeline("ABHA-1")
    assert ev["type"] == "prescription_ocr_digitized" and ev["payload"] == {"candidate_count": 2}
    assert ev["sim_t"] == 100 and ev["source"] == "Bed-A"
    assert client.get("/api/beds/Bed-DEMO/prescriptions/pending").json()["candidates"] == []


def test_prescription_ocr_unreadable_image_is_400(client):
    r = client.post("/api/beds/Bed-A/prescriptions/ocr", files={"file": ("rx.png", b"junk", "image/png")})
    assert r.status_code == 400
    assert r.json()["detail"].startswith("could not read image:")


def first_pending(client, monkeypatch, text="Paracetamol 500mg PO BD"):
    return upload_rx(client, monkeypatch, text).json()["candidates"][0]


def test_approve_prescription_without_correction_uses_ocr_values(client, monkeypatch, db):
    c = first_pending(client, monkeypatch)
    r = client.post(f"/api/beds/Bed-A/prescriptions/pending/{c['id']}/approve")
    assert r.status_code == 200
    o = r.json()
    assert (o["drug"], o["dose"], o["route"], o["frequency_sim_sec"]) == ("Paracetamol", "500mg", "PO", 90)
    assert o["status"] == "active" and o["source"] == "ocr"
    assert o["next_due"] == 100 + 90
    assert [p["source"] for p in db.get_prescriptions("Bed-A")] == ["ocr"]
    assert client.get("/api/beds/Bed-A/prescriptions/pending").json()["candidates"] == []
    types = [e["type"] for e in health_record.get_timeline("ABHA-1")]
    assert types[0] == "prescription_ocr_approved"
    ev = health_record.get_timeline("ABHA-1")[0]
    assert ev["payload"]["raw_line"] == "Paracetamol 500mg PO BD"


def test_approve_prescription_correction_overrides_each_field(client, monkeypatch):
    c = first_pending(client, monkeypatch)
    r = client.post(
        f"/api/beds/Bed-A/prescriptions/pending/{c['id']}/approve",
        json={"drug": "Other", "dose": "1g", "route": "IV", "frequency_sim_sec": 30},
    )
    o = r.json()
    assert (o["drug"], o["dose"], o["route"], o["frequency_sim_sec"], o["next_due"]) == ("Other", "1g", "IV", 30, 130)


def test_approve_prescription_zero_correction_frequency_means_single_dose(client, monkeypatch):
    c = first_pending(client, monkeypatch)
    o = client.post(
        f"/api/beds/Bed-A/prescriptions/pending/{c['id']}/approve", json={"frequency_sim_sec": 0}
    ).json()
    assert o["frequency_sim_sec"] == 0  # 0 is an explicit override, not "fall back to OCR"
    assert o["next_due"] is None


def test_approve_prescription_missing_fields_become_unspecified_and_stat_has_no_due(client, monkeypatch):
    c = first_pending(client, monkeypatch, text="Mystery tablet STAT")
    o = client.post(f"/api/beds/Bed-A/prescriptions/pending/{c['id']}/approve").json()
    assert (o["dose"], o["route"]) == ("(unspecified)", "(unspecified)")
    assert o["frequency_sim_sec"] is None and o["next_due"] is None


def test_prescription_pending_item_errors_and_single_use(client, monkeypatch):
    c = first_pending(client, monkeypatch)
    url = f"/api/beds/Bed-A/prescriptions/pending/{c['id']}"
    assert client.post("/api/beds/Bed-A/prescriptions/pending/zzzz/approve").json()["detail"] == "unknown pending item"
    assert client.post("/api/beds/Bed-A/prescriptions/pending/zzzz/reject").status_code == 404
    assert client.post(url + "/approve").status_code == 200
    assert client.post(url + "/approve").status_code == 404  # already consumed
    assert client.post(url + "/reject").status_code == 404


def test_reject_prescription_logs_event_and_creates_no_order(client, monkeypatch, db):
    c = first_pending(client, monkeypatch)
    r = client.post(f"/api/beds/Bed-A/prescriptions/pending/{c['id']}/reject")
    assert r.json() == {"rejected": True}
    assert db.get_prescriptions("Bed-A") == []
    ev = health_record.get_timeline("ABHA-1")[0]
    assert (ev["type"], ev["payload"]) == ("prescription_ocr_rejected", {"raw_line": "Paracetamol 500mg PO BD"})


# ---------------- lab OCR flow ----------------

def upload_lab(client, monkeypatch, text, bed="Bed-A"):
    monkeypatch.setattr(lab_ocr.pytesseract, "image_to_string", lambda im: text)
    return client.post(f"/api/beds/{bed}/labs/ocr", files={"file": ("lab.png", png(), "image/png")})


def test_lab_ocr_flow_approve_with_and_without_correction(client, monkeypatch):
    r = upload_lab(client, monkeypatch, "Glucose 90 mg/dL (70-110)\nUrea 30 mg/dL\n")
    cands = r.json()["candidates"]
    assert [c["test"] for c in cands] == ["Glucose", "Urea"]
    assert [p["id"] for p in client.get("/api/beds/Bed-A/labs/pending").json()["candidates"]] == [c["id"] for c in cands]

    a = client.post(f"/api/beds/Bed-A/labs/pending/{cands[0]['id']}/approve").json()
    assert (a["test"], a["value"], a["unit"], a["reference_range"], a["flag"]) == ("Glucose", "90", "mg/dL", "70-110", "normal")
    assert a["sim_t"] == 100 and a["raw_line"] == "Glucose 90 mg/dL (70-110)"

    b = client.post(
        f"/api/beds/Bed-A/labs/pending/{cands[1]['id']}/approve",
        json={"test": "BUN", "value": "12", "unit": "u", "reference_range": "1-2", "flag": "high"},
    ).json()
    assert (b["test"], b["value"], b["unit"], b["reference_range"], b["flag"]) == ("BUN", "12", "u", "1-2", "high")

    results = client.get("/api/beds/Bed-A/labs").json()["results"]
    assert [x["test"] for x in results] == ["BUN", "Glucose"]  # newest first (timeline order)


def test_lab_approve_unspecified_value_and_reject(client, monkeypatch):
    c = upload_lab(client, monkeypatch, "Hemoglobin pending").json()["candidates"][0]
    a = client.post(f"/api/beds/Bed-A/labs/pending/{c['id']}/approve").json()
    assert a["value"] == "(unspecified)"
    c2 = upload_lab(client, monkeypatch, "TSH 2.5").json()["candidates"][0]
    assert client.post(f"/api/beds/Bed-A/labs/pending/{c2['id']}/reject").json() == {"rejected": True}
    assert client.get("/api/beds/Bed-A/labs/pending").json()["candidates"] == []
    ev = health_record.get_timeline("ABHA-1")[0]
    assert (ev["type"], ev["payload"]["raw_line"]) == ("lab_result_rejected", "TSH 2.5")
    assert [r["test"] for r in client.get("/api/beds/Bed-A/labs").json()["results"]] == ["Hemoglobin"]


def test_lab_pending_item_errors(client):
    assert client.post("/api/beds/Bed-A/labs/pending/zz/approve").json()["detail"] == "unknown pending item"
    assert client.post("/api/beds/Bed-A/labs/pending/zz/reject").status_code == 404


def test_lab_pending_is_kind_scoped(client, monkeypatch):
    c = first_pending(client, monkeypatch)  # a *prescription* candidate
    assert client.post(f"/api/beds/Bed-A/labs/pending/{c['id']}/approve").status_code == 404


def test_lab_ocr_unreadable_image_is_400(client):
    r = client.post("/api/beds/Bed-A/labs/ocr", files={"file": ("x", b"junk", "image/png")})
    assert r.status_code == 400


# ---------------- discharge summary + record ----------------

def test_discharge_summary_endpoints(client, env):
    r = client.get("/api/beds/Bed-A/discharge-summary").json()
    assert r["available"] is False and "disclaimer" in r
    assert "No discharge summary yet" in client.get("/api/beds/Bed-A/discharge-summary.html").text
    main._discharge("Bed-A", main.bed_identities["Bed-A"], 120)
    r = client.get("/api/beds/Bed-A/discharge-summary").json()
    assert r["available"] is True and r["abha_id"] == "ABHA-1"
    html = client.get("/api/beds/Bed-A/discharge-summary.html")
    assert html.headers["content-type"].startswith("text/html")
    assert "Name 1" in html.text


def test_record_endpoint(client):
    health_record.push_event("ABHA-1", "admission", "Bed-A", 1, {})
    r = client.get("/api/beds/Bed-A/record").json()
    assert r["identity"]["abha_id"] == "ABHA-1"
    assert [e["type"] for e in r["timeline"]] == ["admission"]
    assert "Simulated" in r["disclaimer"]


def test_cors_headers_for_dev_frontend(client):
    ok = client.options("/api/health", headers={"Origin": "http://localhost:5273", "Access-Control-Request-Method": "GET"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5273"
    bad = client.options("/api/health", headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
