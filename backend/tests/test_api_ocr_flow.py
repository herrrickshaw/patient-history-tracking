"""Characterisation tests for the OCR pending-review endpoints in app.main."""
from __future__ import annotations

from app import lab_ocr, main, prescription_ocr

UPLOAD = {"file": ("scan.png", b"not-really-an-image", "image/png")}


def test_unknown_bed_is_404_everywhere(client):
    for path in ("prescriptions/ocr", "labs/ocr"):
        assert client.post(f"/api/beds/nope/{path}", files=UPLOAD).status_code == 404
    assert client.post("/api/beds/nope/labs/pending/x/reject").status_code == 404
    assert client.post("/api/beds/nope/prescriptions/pending/x/reject").status_code == 404


def test_prescription_ocr_approve_with_correction(client, monkeypatch):
    monkeypatch.setattr(prescription_ocr, "extract_text", lambda b: "Paracetamol 650mg PO TDS")
    r = client.post("/api/beds/Bed-1/prescriptions/ocr", files=UPLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["raw_text"] == "Paracetamol 650mg PO TDS"
    (cand,) = body["candidates"]
    assert len(cand["id"]) == 8
    pending = client.get("/api/beds/Bed-1/prescriptions/pending").json()["candidates"]
    assert [p["id"] for p in pending] == [cand["id"]]

    r = client.post(f"/api/beds/Bed-1/prescriptions/pending/{cand['id']}/approve", json={"dose": "500mg"})
    assert r.status_code == 200
    order = r.json()
    assert order["dose"] == "500mg" and order["drug"] == "Paracetamol"
    assert order["frequency_sim_sec"] == 60 and order["next_due"] == 160
    assert order["source"] == "ocr" and order["status"] == "active"
    assert client.get("/api/beds/Bed-1/prescriptions/pending").json()["candidates"] == []
    assert client.get("/api/beds/Bed-1/prescriptions").json()["orders"][0]["source"] == "ocr"
    # second approve of the same id: gone
    assert client.post(f"/api/beds/Bed-1/prescriptions/pending/{cand['id']}/approve").status_code == 404


def test_prescription_unreadable_image_is_400(client):
    r = client.post("/api/beds/Bed-1/prescriptions/ocr", files=UPLOAD)
    assert r.status_code == 400
    assert r.json()["detail"].startswith("could not read image: ")


def test_prescription_reject(client, monkeypatch):
    monkeypatch.setattr(prescription_ocr, "extract_text", lambda b: "Morphine 2mg IV STAT")
    cand = client.post("/api/beds/Bed-1/prescriptions/ocr", files=UPLOAD).json()["candidates"][0]
    r = client.post(f"/api/beds/Bed-1/prescriptions/pending/{cand['id']}/reject")
    assert r.json() == {"rejected": True}
    assert client.post(f"/api/beds/Bed-1/prescriptions/pending/{cand['id']}/reject").status_code == 404


def test_lab_ocr_approve_flows_into_labs_endpoint(client, monkeypatch):
    monkeypatch.setattr(lab_ocr, "extract_text", lambda b: "Hemoglobin 9.5 g/dL (12-16)")
    cand = client.post("/api/beds/Bed-1/labs/ocr", files=UPLOAD).json()["candidates"][0]
    assert client.get("/api/beds/Bed-1/labs").json()["results"] == []
    r = client.post(f"/api/beds/Bed-1/labs/pending/{cand['id']}/approve", json={"value": "10.1"})
    assert r.status_code == 200
    assert r.json() == {
        "test": "Hemoglobin", "value": "10.1", "unit": "g/dL", "reference_range": "12-16",
        "flag": "low", "raw_line": "Hemoglobin 9.5 g/dL (12-16)", "sim_t": 100,
    }
    results = client.get("/api/beds/Bed-1/labs").json()["results"]
    assert [x["value"] for x in results] == ["10.1"]


def test_lab_unreadable_and_reject(client, monkeypatch):
    assert client.post("/api/beds/Bed-1/labs/ocr", files=UPLOAD).status_code == 400
    monkeypatch.setattr(lab_ocr, "extract_text", lambda b: "CRP 40 mg/dL HIGH")
    cand = client.post("/api/beds/Bed-1/labs/ocr", files=UPLOAD).json()["candidates"][0]
    assert client.post(f"/api/beds/Bed-1/labs/pending/{cand['id']}/reject").json() == {"rejected": True}
    assert client.get("/api/beds/Bed-1/labs/pending").json()["candidates"] == []
    # kinds are isolated: a lab id is not a prescription id
    assert client.post(f"/api/beds/Bed-1/prescriptions/pending/{cand['id']}/reject").status_code == 404


def test_timeline_event_types_recorded(client, monkeypatch):
    monkeypatch.setattr(lab_ocr, "extract_text", lambda b: "CRP 40 mg/dL HIGH")
    cand = client.post("/api/beds/Bed-1/labs/ocr", files=UPLOAD).json()["candidates"][0]
    client.post(f"/api/beds/Bed-1/labs/pending/{cand['id']}/reject")
    events = main.health_record.get_timeline("11-2222-3333-4444")
    assert [e["type"] for e in events] == ["lab_result_rejected", "lab_report_digitized"]  # newest first
