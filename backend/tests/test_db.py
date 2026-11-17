from __future__ import annotations


def test_state_roundtrip_and_default(fresh_db):
    assert fresh_db.get_state("sim_t", "0") == "0"
    fresh_db.set_state("sim_t", "7")
    fresh_db.set_state("sim_t", "9")
    assert fresh_db.get_state("sim_t") == "9"


def test_health_timeline_persists_newest_first(fresh_db):
    fresh_db.push_health_event("A", "admission", "Bed-1", 1, {"x": 1})
    fresh_db.push_health_event("A", "discharge", "Bed-1", 2, {})
    assert [e["type"] for e in fresh_db.get_health_timeline("A")] == ["discharge", "admission"]
    assert fresh_db.get_health_timeline("B") == []


def test_pending_queue(fresh_db):
    fresh_db.add_pending("id1", "Bed-1", "lab", {"test": "CRP"})
    assert fresh_db.get_pending_item("id1", "prescription") is None
    assert fresh_db.get_pending_item("id1", "lab")["test"] == "CRP"
    fresh_db.remove_pending("id1")
    assert fresh_db.get_pending("Bed-1", "lab") == []
