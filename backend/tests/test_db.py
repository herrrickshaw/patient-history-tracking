import json

from app import db as appdb


def test_get_conn_creates_parent_dir_reuses_connection_and_enables_wal(db):
    conn = db.get_conn()
    assert db.get_conn() is conn
    assert db.DB_PATH.exists()
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_init_db_is_idempotent(db):
    db.set_state("k", "v")
    db.init_db()
    assert db.get_state("k") == "v"


def test_state_get_default_set_and_overwrite(db):
    assert db.get_state("sim_t") is None
    assert db.get_state("sim_t", "0") == "0"
    db.set_state("sim_t", "5")
    db.set_state("sim_t", "9")
    assert db.get_state("sim_t", "0") == "9"


def test_bed_runtime_defaults_and_independent_setters(db):
    assert db.get_bed_runtime("B") == {"admit_t": 0, "vitals_accum": {}}
    db.set_bed_vitals_accum("B", {"HR": {"min": 1, "max": 2, "last": 2}})
    rt = db.get_bed_runtime("B")
    assert rt["admit_t"] == 0 and rt["vitals_accum"]["HR"]["max"] == 2
    db.set_bed_admit_t("B", 40)  # re-admission clears the accumulator
    assert db.get_bed_runtime("B") == {"admit_t": 40, "vitals_accum": {}}
    db.set_bed_vitals_accum("B", {"HR": {"min": 5, "max": 5, "last": 5}})
    assert db.get_bed_runtime("B")["admit_t"] == 40  # accumulator update keeps admit_t
    assert db.get_bed_runtime("other") == {"admit_t": 0, "vitals_accum": {}}


def test_health_timeline_newest_first_with_payload_roundtrip(db):
    db.push_health_event("P1", "a", "Bed-A", 1, {"x": 1})
    db.push_health_event("P1", "b", "Bed-B", 2, {"y": [1, 2]})
    db.push_health_event("P2", "c", "Bed-C", 3, {})
    tl = db.get_health_timeline("P1")
    assert [e["type"] for e in tl] == ["b", "a"]
    assert tl[0]["source"] == "Bed-B" and tl[0]["sim_t"] == 2 and tl[0]["payload"] == {"y": [1, 2]}
    assert isinstance(tl[0]["wall_time"], float)
    assert db.get_health_timeline("nobody") == []


def test_health_timeline_cap_prunes_oldest_per_patient(db, monkeypatch):
    monkeypatch.setattr(db, "MAX_EVENTS_PER_PATIENT", 3)
    db.push_health_event("Q", "q", "s", 0, {})
    for i in range(5):
        db.push_health_event("P", f"e{i}", "s", i, {})
    assert [e["type"] for e in db.get_health_timeline("P")] == ["e4", "e3", "e2"]
    assert len(db.get_health_timeline("Q")) == 1  # other patients untouched


def test_health_timeline_cap_boundary_exactly_at_limit_keeps_all(db, monkeypatch):
    monkeypatch.setattr(db, "MAX_EVENTS_PER_PATIENT", 3)
    for i in range(3):
        db.push_health_event("P", f"e{i}", "s", i, {})
    assert len(db.get_health_timeline("P")) == 3
    assert appdb.MAX_EVENTS_PER_PATIENT == 3


def order(drug, **kw):
    base = dict(drug=drug, dose="1", route="IV", frequency_sim_sec=10, status="active", next_due=None)
    base.update(kw)
    return base


def test_prescriptions_insert_list_and_defaults(db):
    db.insert_prescriptions("A", [order("d1"), order("d2", source="ocr", next_due=7)])
    db.insert_prescriptions("B", [order("other")])
    rows = db.get_prescriptions("A")
    assert [r["drug"] for r in rows] == ["d1", "d2"]
    assert [r["source"] for r in rows] == ["standard", "ocr"]
    assert rows[1]["next_due"] == 7
    assert set(rows[0]) == {"id", "drug", "dose", "route", "frequency_sim_sec", "status", "next_due", "source"}
    assert db.get_prescriptions("none") == []


def test_active_filter_discontinue_scoped_to_bed_and_administered(db):
    db.insert_prescriptions("A", [order("d1"), order("d2", status="discontinued")])
    db.insert_prescriptions("B", [order("d3")])
    assert [r["drug"] for r in db.get_active_prescriptions("A")] == ["d1"]
    db.discontinue_prescriptions("A")
    assert db.get_active_prescriptions("A") == []
    assert [r["status"] for r in db.get_prescriptions("A")] == ["discontinued", "discontinued"]
    assert [r["status"] for r in db.get_prescriptions("B")] == ["active"]
    (b,) = db.get_prescriptions("B")
    db.mark_prescription_administered(b["id"], 99)
    assert db.get_prescriptions("B")[0]["next_due"] == 99


def test_pending_queue_roundtrip_and_kind_isolation(db):
    db.add_pending("i1", "A", "prescription", {"drug": "x"})
    db.add_pending("i2", "A", "lab", {"test": "t"})
    db.add_pending("i3", "A", "prescription", {"drug": "y"})
    db.add_pending("i4", "B", "prescription", {"drug": "z"})
    assert [p["id"] for p in db.get_pending("A", "prescription")] == ["i1", "i3"]
    assert db.get_pending("A", "lab") == [{"test": "t", "id": "i2"}]
    assert db.get_pending_item("i1", "prescription") == {"drug": "x", "id": "i1"}
    assert db.get_pending_item("i1", "lab") is None  # wrong kind
    assert db.get_pending_item("nope", "lab") is None
    db.remove_pending("i1")
    assert db.get_pending_item("i1", "prescription") is None
    assert [p["id"] for p in db.get_pending("A", "prescription")] == ["i3"]
    db.remove_pending("not-there")  # no error


def test_insurance_record_eligibility_then_claim_upserts_do_not_clobber(db):
    assert db.get_insurance_record("P") is None
    db.upsert_insurance_eligibility("P", "Ins", "POL", "eligible", "AUTH1", 1)
    rec = db.get_insurance_record("P")
    assert (rec["insurer"], rec["eligibility_status"], rec["authorization_ref"]) == ("Ins", "eligible", "AUTH1")
    assert (rec["_checks"], rec["_claims"], rec["last_claim"]) == (1, 0, None)
    db.upsert_insurance_claim("P", "Ins", "POL", {"claim_id": "C1"}, 1)
    rec = db.get_insurance_record("P")
    assert rec["_claims"] == 1 and rec["last_claim"] == {"claim_id": "C1"}
    assert rec["eligibility_status"] == "eligible" and rec["_checks"] == 1
    db.upsert_insurance_eligibility("P", "Ins2", "POL2", "coverage_lapsed", "AUTH2", 2)
    rec = db.get_insurance_record("P")
    assert (rec["insurer"], rec["_checks"], rec["_claims"]) == ("Ins2", 2, 1)
    assert rec["last_claim"] == {"claim_id": "C1"}


def test_claim_before_eligibility_leaves_eligibility_blank(db):
    db.upsert_insurance_claim("P", "I", "POL", {"claim_id": "C"}, 1)
    rec = db.get_insurance_record("P")
    assert rec["eligibility_status"] is None and rec["_checks"] == 0


def test_discharge_summary_latest_is_newest_insert(db):
    assert db.latest_discharge_summary("P") is None
    db.insert_discharge_summary("P", "2030-01-01", {"n": 1})
    db.insert_discharge_summary("P", "2029-01-01", {"n": 2})  # later insert wins even with earlier timestamp
    db.insert_discharge_summary("Q", "2031-01-01", {"n": 9})
    assert db.latest_discharge_summary("P") == {"n": 2}
    assert json.dumps(db.latest_discharge_summary("Q")) == '{"n": 9}'
