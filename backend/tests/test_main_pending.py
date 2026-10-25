"""Approve/reject endpoints (startup events are not run: no VitalDB, no network)."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(fresh_db, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "bed_identities", {
        "BED-A": {"abha_id": "00-0000-0000-000A", "name": "Synthetic A"},
        "BED-B": {"abha_id": "00-0000-0000-000B", "name": "Synthetic B"},
    })
    monkeypatch.setattr(main, "beds", {"BED-A": object(), "BED-B": object()})
    return TestClient(main.app)   # not used as a context manager -> startup hooks skipped


def test_cannot_approve_another_beds_prescription_candidate(client, fresh_db):
    fresh_db.add_pending("rx000001", "BED-A", "prescription",
                         {"raw_line": "Synthdrug 5mg PO OD", "drug": "Synthdrug", "dose": "5mg",
                          "route": "PO", "frequency_abbrev": "OD", "frequency_sim_sec": 120})
    r = client.post("/api/beds/BED-B/prescriptions/pending/rx000001/approve")
    assert r.status_code == 404
    assert fresh_db.get_prescriptions("BED-B") == []
    assert [p["id"] for p in fresh_db.get_pending("BED-A", "prescription")] == ["rx000001"]


def test_cannot_approve_another_beds_lab_candidate(client, fresh_db):
    fresh_db.add_pending("lab00001", "BED-A", "lab",
                         {"raw_line": "Sodium 150", "test": "Sodium", "value": "150", "unit": None,
                          "reference_range": None, "flag": None})
    assert client.post("/api/beds/BED-B/labs/pending/lab00001/approve").status_code == 404
    assert client.post("/api/beds/BED-B/labs/pending/lab00001/reject").status_code == 404
    assert [p["id"] for p in fresh_db.get_pending("BED-A", "lab")] == ["lab00001"]


def test_own_bed_approval_creates_order_with_correction(client, fresh_db):
    fresh_db.add_pending("rx000002", "BED-A", "prescription",
                         {"raw_line": "Synthdrug 5mg", "drug": "Synthdrug", "dose": "5mg",
                          "route": None, "frequency_abbrev": None, "frequency_sim_sec": None})
    r = client.post("/api/beds/BED-A/prescriptions/pending/rx000002/approve", json={"route": "PO"})
    assert r.status_code == 200
    body = r.json()
    assert (body["drug"], body["dose"], body["route"], body["next_due"]) == ("Synthdrug", "5mg", "PO", None)
    assert fresh_db.get_pending("BED-A", "prescription") == []
