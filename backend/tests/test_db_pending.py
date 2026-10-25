"""OCR pending queue: a candidate belongs to the bed (patient) it was scanned for."""


def test_pending_item_round_trip(fresh_db):
    fresh_db.add_pending("item0001", "BED-A", "lab", {"test": "Sodium", "value": "140"})
    assert [p["id"] for p in fresh_db.get_pending("BED-A", "lab")] == ["item0001"]
    assert fresh_db.get_pending("BED-A", "prescription") == []
    fresh_db.remove_pending("item0001")
    assert fresh_db.get_pending("BED-A", "lab") == []


def test_pending_item_is_not_visible_under_another_bed(fresh_db):
    """approve/reject looked items up by id only, so bed B's URL could approve bed A's
    OCR candidate into bed B's patient record."""
    fresh_db.add_pending("item0002", "BED-A", "prescription", {"drug": "Synthdrug"})
    assert fresh_db.get_pending_item("item0002", "prescription", bed_id="BED-B") is None
    assert fresh_db.get_pending_item("item0002", "prescription", bed_id="BED-A")["drug"] == "Synthdrug"
