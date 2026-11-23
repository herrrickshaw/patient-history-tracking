"""The simulation engine inside main.py: admit/discharge cycle, event
recording, clock loop, startup wiring and the two WebSocket feeds."""
import asyncio

import numpy as np
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app import alerts, health_record, insurance_connect, prescriptions

from test_main_http import FakeBed, identity


@pytest.fixture
def world(db, monkeypatch):
    bed = FakeBed(case_id=11, encounter_length=100)
    monkeypatch.setattr(main, "beds", {"Bed-A": bed})
    monkeypatch.setattr(main, "bed_identities", {"Bed-A": identity(1)})
    monkeypatch.setattr(main, "sim_t", 0)
    return bed


def types(abha="ABHA-1"):
    return [e["type"] for e in reversed(health_record.get_timeline(abha))]


# ---------------- vitals accumulator ----------------

def test_update_vitals_accum_tracks_min_max_last_and_skips_none(db):
    main._update_vitals_accum("B", {"HR": 80, "RR": None})
    main._update_vitals_accum("B", {"HR": 70})
    main._update_vitals_accum("B", {"HR": 90, "RR": 12})
    main._update_vitals_accum("B", {"HR": 85})
    acc = db.get_bed_runtime("B")["vitals_accum"]
    assert acc["HR"] == {"min": 70, "max": 90, "last": 85}
    assert acc["RR"] == {"min": 12, "max": 12, "last": 12}


# ---------------- admit ----------------

def test_admit_records_events_orders_and_due_times(world, db):
    ident = main.bed_identities["Bed-A"]
    main._admit("Bed-A", ident, sim_t=40)
    assert db.get_bed_runtime("Bed-A")["admit_t"] == 40
    assert types() == ["admission", "insurance_eligibility_checked", "prescription_ordered"]
    orders = db.get_prescriptions("Bed-A")
    expected = prescriptions.generate_orders("General surgery")
    assert [o["drug"] for o in orders] == [o["drug"] for o in expected]
    for o in orders:
        if o["frequency_sim_sec"]:
            assert o["next_due"] == 40 + o["frequency_sim_sec"]
        else:
            assert o["next_due"] is None  # continuous infusion has no repeat due time
    assert any(o["frequency_sim_sec"] == 0 for o in orders)
    elig = health_record.get_timeline("ABHA-1")[1]
    assert elig["type"] == "insurance_eligibility_checked" and elig["payload"]["status"] in ("eligible", "coverage_lapsed")


def test_resume_or_admit_only_admits_when_no_persisted_prescriptions(world, db, monkeypatch):
    ident = main.bed_identities["Bed-A"]
    monkeypatch.setattr(main, "sim_t", 7)
    main._resume_or_admit("Bed-A", ident)
    assert db.get_bed_runtime("Bed-A")["admit_t"] == 7
    n = len(db.get_prescriptions("Bed-A"))
    main._resume_or_admit("Bed-A", ident)  # persisted state exists -> no second admission
    assert len(db.get_prescriptions("Bed-A")) == n
    assert types().count("admission") == 1


# ---------------- discharge ----------------

def test_discharge_builds_summary_from_encounter_window_only(world, db):
    ident = main.bed_identities["Bed-A"]
    main._admit("Bed-A", ident, sim_t=50)
    # events before admission are outside the encounter window, in-window ones are kept
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 10, {"vital": "OLD", "message": "old"})
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 60, {"vital": "HR", "message": "in"})
    health_record.push_event("ABHA-1", "medication_administered", "Bed-A", 70, {"drug": "D", "dose": "1", "route": "IV"})
    health_record.push_event("ABHA-1", "lab_result_approved", "Bed-A", 80, {"test": "T", "value": "1", "unit": None, "reference_range": None, "flag": None})
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 200, {"vital": "FUT", "message": "future"})
    main._update_vitals_accum("Bed-A", {"HR": 77})
    main._discharge("Bed-A", ident, sim_t=120)

    s = main.discharge_summary.latest("ABHA-1")
    assert (s["admitted_sim_t"], s["discharged_sim_t"], s["duration_sim_sec"]) == (50, 120, 70)
    assert [e["payload"]["vital"] for e in s["alerts"]] == ["HR"]
    assert [e["payload"]["drug"] for e in s["medications"]] == ["D"]
    assert [e["payload"]["test"] for e in s["lab_results"]] == ["T"]
    assert s["vitals_range"]["HR"] == {"min": 77, "max": 77, "last": 77}
    assert s["insurance_claim"]["claim_id"].startswith("CLM-")
    assert insurance_connect.get_record("ABHA-1")["_claims"] == 1
    assert all(o["status"] == "discontinued" for o in db.get_prescriptions("Bed-A"))
    tail = types()[-4:]
    assert tail == ["discharge", "insurance_claim_submitted", "prescription_discontinued", "discharge_summary_ready"]


def test_discharge_alerts_are_chronological(world):
    ident = main.bed_identities["Bed-A"]
    main._admit("Bed-A", ident, sim_t=0)
    for t, v in [(5, "A"), (6, "B"), (7, "C")]:
        health_record.push_event("ABHA-1", "alert_raised", "Bed-A", t, {"vital": v, "message": v})
    main._discharge("Bed-A", ident, sim_t=50)
    s = main.discharge_summary.latest("ABHA-1")
    assert [e["payload"]["vital"] for e in s["alerts"]] == ["A", "B", "C"]


def test_discharge_window_boundaries_inclusive(world):
    ident = main.bed_identities["Bed-A"]
    main._admit("Bed-A", ident, sim_t=10)
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 10, {"vital": "AT_START", "message": "m"})
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 30, {"vital": "AT_END", "message": "m"})
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 9, {"vital": "BEFORE", "message": "m"})
    health_record.push_event("ABHA-1", "alert_raised", "Bed-A", 31, {"vital": "AFTER", "message": "m"})
    main._discharge("Bed-A", ident, sim_t=30)
    got = {e["payload"]["vital"] for e in main.discharge_summary.latest("ABHA-1")["alerts"]}
    assert got == {"AT_START", "AT_END"}


# ---------------- _record_events ----------------

def run_record(t, last_alert_keys=None, last_cycle=None):
    lak = last_alert_keys if last_alert_keys is not None else {"Bed-A": set()}
    lc = last_cycle if last_cycle is not None else {"Bed-A": 0}
    main._record_events(t, lak, lc)
    return lak, lc


def alert_vitals(world):
    """Return a vitals dict that trips exactly the first RULES entry (read from the table itself)."""
    key, lo_c = alerts.RULES[0][0], alerts.RULES[0][1]
    world.vitals = {key: lo_c}
    return key


def test_alert_raised_once_then_resolved(world):
    key = alert_vitals(world)
    lak, lc = run_record(1)
    assert lak["Bed-A"] == {key}
    run_record(2, lak, lc)  # still alarming: no duplicate event
    assert [e["type"] for e in health_record.get_timeline("ABHA-1")].count("alert_raised") == 1
    world.vitals = {}
    run_record(3, lak, lc)
    ev = health_record.get_timeline("ABHA-1")[0]
    assert (ev["type"], ev["payload"]) == ("alert_resolved", {"vital": key})
    assert lak["Bed-A"] == set()
    run_record(4, lak, lc)
    assert [e["type"] for e in health_record.get_timeline("ABHA-1")].count("alert_resolved") == 1


def test_new_alert_for_second_vital_is_raised_separately(world):
    k1, lo1 = alerts.RULES[0][0], alerts.RULES[0][1]
    k2, lo2 = alerts.RULES[1][0], alerts.RULES[1][1]
    world.vitals = {k1: lo1}
    lak, lc = run_record(1)
    world.vitals = {k1: lo1, k2: lo2}
    run_record(2, lak, lc)
    raised = [e["payload"]["vital"] for e in reversed(health_record.get_timeline("ABHA-1")) if e["type"] == "alert_raised"]
    assert raised == [k1, k2]


def test_vitals_snapshot_every_sixty_sim_seconds(world):
    world.vitals = {"HR": 1.0}
    run_record(59)
    assert "vitals_snapshot" not in types()
    run_record(60)
    ev = health_record.get_timeline("ABHA-1")[0]
    assert ev["type"] == "vitals_snapshot" and ev["payload"] == {"HR": 1.0}
    run_record(0)  # t % 60 == 0 also at 0
    assert types().count("vitals_snapshot") == 2


def test_medication_due_logic_and_rescheduling(world, db):
    db.insert_prescriptions("Bed-A", [
        dict(drug="due", dose="1", route="IV", frequency_sim_sec=10, status="active", next_due=20),
        dict(drug="later", dose="1", route="IV", frequency_sim_sec=10, status="active", next_due=21),
        dict(drug="infusion", dose="1", route="IV", frequency_sim_sec=0, status="active", next_due=None),
        dict(drug="stopped", dose="1", route="IV", frequency_sim_sec=10, status="discontinued", next_due=0),
    ])
    run_record(20)
    meds = [e["payload"]["drug"] for e in health_record.get_timeline("ABHA-1") if e["type"] == "medication_administered"]
    assert meds == ["due"]  # t == next_due is administered (>=), others are not
    nd = {p["drug"]: p["next_due"] for p in db.get_prescriptions("Bed-A")}
    assert nd == {"due": 30, "later": 21, "infusion": None, "stopped": 0}
    run_record(29)
    assert types().count("medication_administered") == 2  # "later" came due at 21 (<= 29)
    run_record(30)
    assert types().count("medication_administered") == 3


def test_cycle_rollover_discharges_readmits_and_clears_alert_state(world, db):
    ident = main.bed_identities["Bed-A"]
    main._admit("Bed-A", ident, 0)
    key = alert_vitals(world)
    lak, lc = run_record(99, {"Bed-A": {"stale"}}, {"Bed-A": 0})
    assert "discharge" not in types()  # 99 // 100 == 0, same cycle
    world.vitals = {}
    lak, lc = run_record(100, lak, lc)
    assert lc["Bed-A"] == 1
    t = types()
    assert t.count("admission") == 2 and t.count("discharge") == 1 and t.count("insurance_claim_submitted") == 1
    assert db.get_bed_runtime("Bed-A")["admit_t"] == 100
    assert lak["Bed-A"] == set()  # previous encounter's alarms do not carry over
    assert [p["status"] for p in db.get_prescriptions("Bed-A")][:4] == ["discontinued"] * 4
    assert any(p["status"] == "active" for p in db.get_prescriptions("Bed-A"))


def test_no_rollover_when_cycle_unchanged(world):
    run_record(150, last_cycle={"Bed-A": 1})
    assert "discharge" not in types()


# ---------------- startup hooks ----------------

def test_init_persistence_resumes_sim_clock(db, monkeypatch):
    monkeypatch.setattr(main, "sim_t", 0)
    db.set_state("sim_t", "321")
    main.init_persistence()
    assert main.sim_t == 321


def test_init_persistence_defaults_to_zero(db, monkeypatch):
    monkeypatch.setattr(main, "sim_t", 5)
    main.init_persistence()
    assert main.sim_t == 0


def test_load_beds_assigns_cases_and_demo_bed(db, monkeypatch, vitaldb_fake):
    monkeypatch.setattr(main, "beds", {})
    monkeypatch.setattr(main, "bed_identities", {})
    monkeypatch.setattr(main, "sim_t", 0)
    monkeypatch.setattr(main.vitals_source, "pick_case_ids", lambda n: list(range(200, 200 + n)))
    monkeypatch.setattr(main.vitals_source, "BedSource", lambda bed_id, cid, encounter_length=None: FakeBed(case_id=cid, encounter_length=encounter_length or 10))
    monkeypatch.setattr(main.patient_identity, "build_identity", lambda bed_id, cid: identity(cid, bed_id=bed_id))
    main.load_beds()
    assert list(main.beds) == [f"Bed-{c}" for c in "ABCDEF"] + [main.DEMO_BED_ID]
    assert main.beds["Bed-C"].case_id == 202
    assert main.beds[main.DEMO_BED_ID].case_id == 206
    assert main.beds[main.DEMO_BED_ID].encounter_length == main.DEMO_ENCOUNTER_SIM_SEC
    demo = main.bed_identities[main.DEMO_BED_ID]
    assert demo["is_demo"] is True and demo["name"].endswith("(fast-cycle demo)")
    assert "is_demo" not in main.bed_identities["Bed-A"]
    assert all(db.get_prescriptions(b) for b in main.beds)  # every bed was admitted


def test_clock_loop_advances_persists_and_records(world, db, monkeypatch):
    seen = []
    calls = {"n": 0}
    real_sleep = asyncio.sleep

    async def fake_sleep(sec):
        calls["n"] += 1
        if calls["n"] > 3:
            raise RuntimeError("stop")
        await real_sleep(0)

    def fake_record(t, lak, lc):
        seen.append(t)

    monkeypatch.setattr(main, "_record_events", fake_record)
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    tasks = []
    real_create = asyncio.create_task
    monkeypatch.setattr(main.asyncio, "create_task", lambda coro: tasks.append(real_create(coro)) or tasks[-1])

    async def run():
        await main.start_clock()
        with pytest.raises(RuntimeError, match="stop"):
            await tasks[0]

    asyncio.run(run())
    step = main.SIM_SECONDS_PER_TICK
    assert seen == [step, 2 * step, 3 * step]
    assert main.sim_t == 3 * step
    assert db.get_state("sim_t") == str(3 * step)


# ---------------- websockets ----------------

def test_ws_vitals_sends_tick_with_vitals_and_alerts(world, monkeypatch):
    key, lo = alerts.RULES[0][0], alerts.RULES[0][1]
    world.vitals = {key: lo}
    monkeypatch.setattr(main, "sim_t", 8)
    with TestClient(main.app).websocket_connect("/ws/vitals") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "tick"
    (b,) = msg["beds"]
    assert (b["bed_id"], b["case_id"], b["sim_t"], b["vitals"]) == ("Bed-A", 11, 8, {key: lo})
    assert [a["vital"] for a in b["alerts"]] == [key]


def test_ws_vitals_only_sends_when_sim_time_changes(world, monkeypatch):
    monkeypatch.setattr(main, "REAL_TICK_SEC", 0.0)
    monkeypatch.setattr(main, "sim_t", 4)
    with TestClient(main.app).websocket_connect("/ws/vitals") as ws:
        assert ws.receive_json()["beds"][0]["sim_t"] == 4
        monkeypatch.setattr(main, "sim_t", 8)
        assert ws.receive_json()["beds"][0]["sim_t"] == 8


def test_ws_waveform_unknown_bed_closed_with_4404(world):
    with pytest.raises(Exception) as ei:
        with TestClient(main.app).websocket_connect("/ws/waveform/nope"):
            pass
    assert getattr(ei.value, "code", None) == 4404


def test_ws_waveform_streams_window_between_ticks(world, monkeypatch):
    class WaveBed(FakeBed):
        def ensure_waveform_loaded(self):
            self.waveform_loaded = True

        def waveform_window(self, a, b):
            return {"ECG": [float(a), float(b)], "PLETH": [None]}

    wb = WaveBed(case_id=11)
    monkeypatch.setattr(main, "beds", {"Bed-A": wb})
    monkeypatch.setattr(main, "REAL_TICK_SEC", 0.0)
    monkeypatch.setattr(main, "sim_t", 4)
    with TestClient(main.app).websocket_connect("/ws/waveform/Bed-A") as ws:
        assert wb.waveform_loaded
        monkeypatch.setattr(main, "sim_t", 12)
        msg = ws.receive_json()
    assert msg == {"type": "wave", "bed_id": "Bed-A", "sim_t": 12, "ECG": [4.0, 12.0], "PLETH": [None]}


class DisconnectingWS:
    """Minimal WebSocket stand-in whose first send fails like a closed socket."""

    def __init__(self):
        self.accepted = False
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        from fastapi import WebSocketDisconnect

        self.sent.append(data)
        raise WebSocketDisconnect()


def test_ws_vitals_returns_cleanly_when_client_disconnects(world, monkeypatch, caplog):
    monkeypatch.setattr(main, "sim_t", 4)
    ws = DisconnectingWS()
    with caplog.at_level("INFO", logger="icu-dashboard"):
        asyncio.run(main.ws_vitals(ws))
    assert ws.accepted and len(ws.sent) == 1
    assert "client disconnected" in caplog.text


def test_ws_waveform_returns_cleanly_when_client_disconnects(world, monkeypatch, caplog):
    class WaveBed(FakeBed):
        def ensure_waveform_loaded(self):
            pass

        def waveform_window(self, a, b):
            return {"ECG": [], "PLETH": []}

    monkeypatch.setattr(main, "beds", {"Bed-A": WaveBed()})
    monkeypatch.setattr(main, "sim_t", 4)
    monkeypatch.setattr(main, "REAL_TICK_SEC", 0.0)
    ws = DisconnectingWS()

    async def run():
        task = asyncio.create_task(main.ws_waveform(ws, "Bed-A"))
        await asyncio.sleep(0)
        main.sim_t = 8  # a new tick arrives -> the server tries to send and finds the socket closed
        await asyncio.wait_for(task, timeout=3)

    with caplog.at_level("INFO", logger="icu-dashboard"):
        asyncio.run(run())
    assert len(ws.sent) == 1
    assert "waveform client disconnected for Bed-A" in caplog.text
