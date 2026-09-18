"""ICU dashboard analogue backend.

Streams real (de-identified) bedside-monitor vitals from VitalDB's open
dataset over a WebSocket, evaluates threshold alarms, and exposes a
small REST surface for the bed roster -- the software layer an
IntelliICU-style product puts on top of connected monitors, pumps, and
ventilators.

Persistent state (prescriptions, OCR review queues, vitals ranges,
the health-record timeline, insurance records, discharge summaries)
lives in SQLite via backend/app/db.py -- a restart resumes the same
session instead of erasing it. Only the VitalDB case assignment
(beds/bed_identities below) is recomputed fresh each startup, since
it's a pure function of the case id and cheap to redo.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid

from fastapi import Body, FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import (
    alerts,
    db,
    discharge_summary,
    health_record,
    insurance_connect,
    lab_ocr,
    patient_identity,
    prescription_ocr,
    prescriptions,
    vitals_source,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("icu-dashboard")

NUM_BEDS = 6
REAL_TICK_SEC = 1.0
SIM_SECONDS_PER_TICK = 4  # playback speed-up so a ~90min case cycles in a demo-friendly window

DEMO_BED_ID = "Bed-DEMO"
DEMO_ENCOUNTER_SIM_SEC = 40  # ~10 real seconds at 4x playback -- watch a full admit/discharge/claim cycle live

app = FastAPI(title="ICU Dashboard Analogue")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5273", "http://127.0.0.1:5273"],
    allow_methods=["*"],
    allow_headers=["*"],
)

beds: dict[str, vitals_source.BedSource] = {}
bed_identities: dict[str, dict] = {}
VITALS_SNAPSHOT_EVERY_SIM_SEC = 60

# Single shared sim-time clock so every connected client (the bed grid
# and any open waveform detail views) plays back the same moment.
# Persisted to SQLite (app_state) so a restart resumes instead of
# rewinding to 0.
sim_t = 0


@app.on_event("startup")
def init_persistence() -> None:
    db.init_db()
    global sim_t
    sim_t = int(db.get_state("sim_t", "0"))
    log.info("resuming sim clock at t=%s from persisted state", sim_t)


@app.on_event("startup")
def load_beds() -> None:
    case_ids = vitals_source.pick_case_ids(NUM_BEDS + 1)  # +1 distinct case for the fast-cycle demo bed
    labels = [chr(ord("A") + i) for i in range(NUM_BEDS)]
    for label, case_id in zip(labels, case_ids[:NUM_BEDS]):
        bed_id = f"Bed-{label}"
        log.info("loading %s <- VitalDB case %s", bed_id, case_id)
        beds[bed_id] = vitals_source.BedSource(bed_id, case_id)
        identity = patient_identity.build_identity(bed_id, case_id)
        bed_identities[bed_id] = identity
        _resume_or_admit(bed_id, identity)

    demo_case_id = case_ids[NUM_BEDS]
    log.info("loading %s <- VitalDB case %s (fast-cycle demo)", DEMO_BED_ID, demo_case_id)
    beds[DEMO_BED_ID] = vitals_source.BedSource(DEMO_BED_ID, demo_case_id, encounter_length=DEMO_ENCOUNTER_SIM_SEC)
    demo_identity = patient_identity.build_identity(DEMO_BED_ID, demo_case_id)
    demo_identity["name"] = f"{demo_identity['name']} (fast-cycle demo)"
    demo_identity["is_demo"] = True
    bed_identities[DEMO_BED_ID] = demo_identity
    _resume_or_admit(DEMO_BED_ID, demo_identity)


def _resume_or_admit(bed_id: str, identity: dict) -> None:
    """First-ever startup for this bed admits fresh; a restart with
    existing persisted state (prescriptions already on file) resumes
    the session in place instead of re-admitting over it."""
    if db.get_prescriptions(bed_id):
        log.info("%s has persisted state, resuming rather than re-admitting", bed_id)
    else:
        _admit(bed_id, identity, sim_t=sim_t)


@app.on_event("startup")
async def start_clock() -> None:
    async def clock_loop():
        global sim_t
        last_alert_keys: dict[str, set[str]] = {bed_id: set() for bed_id in beds}
        last_cycle: dict[str, int] = {bed_id: sim_t // beds[bed_id].encounter_length for bed_id in beds}
        while True:
            await asyncio.sleep(REAL_TICK_SEC)
            sim_t += SIM_SECONDS_PER_TICK
            db.set_state("sim_t", str(sim_t))
            _record_events(sim_t, last_alert_keys, last_cycle)

    asyncio.create_task(clock_loop())


def _update_vitals_accum(bed_id: str, vitals: dict) -> None:
    accum = db.get_bed_runtime(bed_id)["vitals_accum"]
    for key, value in vitals.items():
        if value is None:
            continue
        entry = accum.setdefault(key, {"min": value, "max": value, "last": value})
        entry["min"] = min(entry["min"], value)
        entry["max"] = max(entry["max"], value)
        entry["last"] = value
    db.set_bed_vitals_accum(bed_id, accum)


def _admit(bed_id: str, identity: dict, sim_t: int) -> None:
    db.set_bed_admit_t(bed_id, sim_t)
    health_record.push_event(
        identity["abha_id"], "admission", source=bed_id, sim_t=sim_t,
        payload={"department": identity["department"], "procedure": identity["procedure"]},
    )
    eligibility = insurance_connect.check_eligibility(identity["abha_id"])
    health_record.push_event(
        identity["abha_id"], "insurance_eligibility_checked", source=bed_id, sim_t=sim_t, payload=eligibility,
    )

    orders = prescriptions.generate_orders(identity["department"])
    for order in orders:
        order["next_due"] = sim_t + order["frequency_sim_sec"] if order["frequency_sim_sec"] else None
    db.insert_prescriptions(bed_id, orders)
    health_record.push_event(
        identity["abha_id"], "prescription_ordered", source=bed_id, sim_t=sim_t,
        payload={"drugs": [o["drug"] for o in orders]},
    )


def _discharge(bed_id: str, identity: dict, sim_t: int) -> None:
    abha_id = identity["abha_id"]
    admitted_t = db.get_bed_runtime(bed_id)["admit_t"]
    encounter_events = [e for e in health_record.get_timeline(abha_id) if admitted_t <= e["sim_t"] <= sim_t]
    alert_events = [e for e in reversed(encounter_events) if e["type"] == "alert_raised"]
    medication_events = [e for e in reversed(encounter_events) if e["type"] == "medication_administered"]
    lab_events = [e for e in reversed(encounter_events) if e["type"] == "lab_result_approved"]

    health_record.push_event(abha_id, "discharge", source=bed_id, sim_t=sim_t, payload={})
    claim = insurance_connect.submit_claim(
        abha_id, {"department": identity["department"], "procedure": identity["procedure"]},
    )
    health_record.push_event(abha_id, "insurance_claim_submitted", source=bed_id, sim_t=sim_t, payload=claim)

    db.discontinue_prescriptions(bed_id)
    health_record.push_event(abha_id, "prescription_discontinued", source=bed_id, sim_t=sim_t, payload={})

    vitals_range = db.get_bed_runtime(bed_id)["vitals_accum"]
    discharge_summary.build(
        identity, admitted_t, sim_t, vitals_range, alert_events, medication_events, claim, lab_events,
    )
    health_record.push_event(abha_id, "discharge_summary_ready", source=bed_id, sim_t=sim_t, payload={})


def _record_events(t: int, last_alert_keys: dict[str, set[str]], last_cycle: dict[str, int]) -> None:
    for bed_id, src in beds.items():
        identity = bed_identities[bed_id]
        abha_id = identity["abha_id"]

        cycle = t // src.encounter_length
        if cycle > last_cycle[bed_id]:
            _discharge(bed_id, identity, t)
            _admit(bed_id, identity, t)
            last_cycle[bed_id] = cycle
            last_alert_keys[bed_id] = set()  # new encounter, previous alarms don't carry over

        for order in db.get_active_prescriptions(bed_id):
            if order["next_due"] is not None and t >= order["next_due"]:
                health_record.push_event(
                    abha_id, "medication_administered", source=bed_id, sim_t=t,
                    payload={"drug": order["drug"], "dose": order["dose"], "route": order["route"]},
                )
                db.mark_prescription_administered(order["id"], t + order["frequency_sim_sec"])

        vitals = src.tick(t)
        _update_vitals_accum(bed_id, vitals)
        current = alerts.evaluate(vitals)
        current_keys = {a["vital"] for a in current}
        prev_keys = last_alert_keys[bed_id]

        for a in current:
            if a["vital"] not in prev_keys:
                health_record.push_event(abha_id, "alert_raised", source=bed_id, sim_t=t, payload=a)
        for vital in prev_keys - current_keys:
            health_record.push_event(
                abha_id, "alert_resolved", source=bed_id, sim_t=t, payload={"vital": vital},
            )
        last_alert_keys[bed_id] = current_keys

        if t % VITALS_SNAPSHOT_EVERY_SIM_SEC == 0:
            health_record.push_event(abha_id, "vitals_snapshot", source=bed_id, sim_t=t, payload=vitals)


@app.get("/api/beds")
def list_beds():
    return [
        {
            "bed_id": bed_id,
            "source": f"VitalDB case #{src.case_id}",
            "length_sec": src.length,
            "encounter_length_sec": src.encounter_length,
            "is_demo": bed_identities.get(bed_id, {}).get("is_demo", False),
        }
        for bed_id, src in beds.items()
    ]


@app.get("/api/health")
def health():
    return {"status": "ok", "beds_loaded": len(beds)}


@app.get("/api/beds/{bed_id}/identity")
def bed_identity(bed_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    return identity


@app.get("/api/beds/{bed_id}/insurance")
def bed_insurance(bed_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    record = insurance_connect.get_record(identity["abha_id"]) or {}
    return {
        "disclaimer": insurance_connect.DISCLAIMER,
        "abha_id": identity["abha_id"],
        **{k: v for k, v in record.items() if not k.startswith("_")},
    }


@app.get("/api/beds/{bed_id}/prescriptions")
def bed_prescriptions_endpoint(bed_id: str):
    if bed_id not in beds:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    return {
        "disclaimer": prescriptions.DISCLAIMER,
        "orders": db.get_prescriptions(bed_id),
    }


@app.post("/api/beds/{bed_id}/prescriptions/ocr")
async def bed_prescriptions_ocr(bed_id: str, file: UploadFile = File(...)):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")

    image_bytes = await file.read()
    try:
        raw_text = prescription_ocr.extract_text(image_bytes)
    except Exception as exc:  # pytesseract/PIL raise on unreadable/corrupt images
        raise HTTPException(status_code=400, detail=f"could not read image: {exc}") from exc

    candidates = prescription_ocr.parse_candidates(raw_text)
    for c in candidates:
        item_id = uuid.uuid4().hex[:8]
        db.add_pending(item_id, bed_id, "prescription", c)
        c["id"] = item_id

    health_record.push_event(
        identity["abha_id"], "prescription_ocr_digitized", source=bed_id, sim_t=sim_t,
        payload={"candidate_count": len(candidates)},
    )
    return {"disclaimer": prescription_ocr.DISCLAIMER, "raw_text": raw_text, "candidates": candidates}


@app.get("/api/beds/{bed_id}/prescriptions/pending")
def bed_prescriptions_pending(bed_id: str):
    if bed_id not in beds:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    return {"disclaimer": prescription_ocr.DISCLAIMER, "candidates": db.get_pending(bed_id, "prescription")}


class PrescriptionCorrection(BaseModel):
    drug: str | None = None
    dose: str | None = None
    route: str | None = None
    frequency_sim_sec: int | None = None


@app.post("/api/beds/{bed_id}/prescriptions/pending/{item_id}/approve")
def approve_pending_prescription(bed_id: str, item_id: str, correction: PrescriptionCorrection = Body(default=None)):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    match = db.get_pending_item(item_id, "prescription")
    if match is None:
        raise HTTPException(status_code=404, detail="unknown pending item")
    db.remove_pending(item_id)

    correction = correction or PrescriptionCorrection()
    drug = correction.drug or match["drug"]
    dose = correction.dose or match["dose"] or "(unspecified)"
    route = correction.route or match["route"] or "(unspecified)"
    freq = correction.frequency_sim_sec if correction.frequency_sim_sec is not None else match["frequency_sim_sec"]

    order = {
        "drug": drug,
        "dose": dose,
        "route": route,
        "frequency_sim_sec": freq,
        "status": "active",
        "next_due": sim_t + freq if freq else None,
        "source": "ocr",
    }
    db.insert_prescriptions(bed_id, [order])
    health_record.push_event(
        identity["abha_id"], "prescription_ocr_approved", source=bed_id, sim_t=sim_t,
        payload={**order, "raw_line": match["raw_line"]},
    )
    return order


@app.post("/api/beds/{bed_id}/prescriptions/pending/{item_id}/reject")
def reject_pending_prescription(bed_id: str, item_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    match = db.get_pending_item(item_id, "prescription")
    if match is None:
        raise HTTPException(status_code=404, detail="unknown pending item")
    db.remove_pending(item_id)
    health_record.push_event(
        identity["abha_id"], "prescription_ocr_rejected", source=bed_id, sim_t=sim_t,
        payload={"raw_line": match["raw_line"]},
    )
    return {"rejected": True}


@app.post("/api/beds/{bed_id}/labs/ocr")
async def bed_labs_ocr(bed_id: str, file: UploadFile = File(...)):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")

    image_bytes = await file.read()
    try:
        raw_text = lab_ocr.extract_text(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"could not read image: {exc}") from exc

    candidates = lab_ocr.parse_candidates(raw_text)
    for c in candidates:
        item_id = uuid.uuid4().hex[:8]
        db.add_pending(item_id, bed_id, "lab", c)
        c["id"] = item_id

    health_record.push_event(
        identity["abha_id"], "lab_report_digitized", source=bed_id, sim_t=sim_t,
        payload={"candidate_count": len(candidates)},
    )
    return {"disclaimer": lab_ocr.DISCLAIMER, "raw_text": raw_text, "candidates": candidates}


@app.get("/api/beds/{bed_id}/labs/pending")
def bed_labs_pending(bed_id: str):
    if bed_id not in beds:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    return {"disclaimer": lab_ocr.DISCLAIMER, "candidates": db.get_pending(bed_id, "lab")}


@app.get("/api/beds/{bed_id}/labs")
def bed_labs(bed_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    results = [e for e in health_record.get_timeline(identity["abha_id"]) if e["type"] == "lab_result_approved"]
    return {"disclaimer": lab_ocr.DISCLAIMER, "results": [e["payload"] for e in results]}


class LabCorrection(BaseModel):
    test: str | None = None
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None


@app.post("/api/beds/{bed_id}/labs/pending/{item_id}/approve")
def approve_pending_lab(bed_id: str, item_id: str, correction: LabCorrection = Body(default=None)):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    match = db.get_pending_item(item_id, "lab")
    if match is None:
        raise HTTPException(status_code=404, detail="unknown pending item")
    db.remove_pending(item_id)

    correction = correction or LabCorrection()
    result = {
        "test": correction.test or match["test"],
        "value": correction.value or match["value"] or "(unspecified)",
        "unit": correction.unit or match["unit"],
        "reference_range": correction.reference_range or match["reference_range"],
        "flag": correction.flag or match["flag"],
        "raw_line": match["raw_line"],
        "sim_t": sim_t,
    }
    health_record.push_event(identity["abha_id"], "lab_result_approved", source=bed_id, sim_t=sim_t, payload=result)
    return result


@app.post("/api/beds/{bed_id}/labs/pending/{item_id}/reject")
def reject_pending_lab(bed_id: str, item_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    match = db.get_pending_item(item_id, "lab")
    if match is None:
        raise HTTPException(status_code=404, detail="unknown pending item")
    db.remove_pending(item_id)
    health_record.push_event(
        identity["abha_id"], "lab_result_rejected", source=bed_id, sim_t=sim_t, payload={"raw_line": match["raw_line"]},
    )
    return {"rejected": True}


@app.get("/api/beds/{bed_id}/discharge-summary")
def bed_discharge_summary(bed_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    summary = discharge_summary.latest(identity["abha_id"])
    if summary is None:
        return {"available": False, "disclaimer": discharge_summary.DISCLAIMER}
    return {"available": True, **summary}


@app.get("/api/beds/{bed_id}/discharge-summary.html", response_class=HTMLResponse)
def bed_discharge_summary_html(bed_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    summary = discharge_summary.latest(identity["abha_id"])
    if summary is None:
        return HTMLResponse("<p>No discharge summary yet -- this encounter hasn't been discharged.</p>")
    return HTMLResponse(discharge_summary.render_html(summary))


@app.get("/api/beds/{bed_id}/record")
def bed_record(bed_id: str):
    identity = bed_identities.get(bed_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="unknown bed_id")
    return {
        "identity": identity,
        "disclaimer": health_record.DISCLAIMER,
        "timeline": health_record.get_timeline(identity["abha_id"]),
    }


@app.websocket("/ws/vitals")
async def ws_vitals(ws: WebSocket):
    await ws.accept()
    last_t = None
    try:
        while True:
            frame_start = time.monotonic()
            t = sim_t
            if t != last_t:
                payload = []
                for bed_id, src in beds.items():
                    vitals = src.tick(t)
                    payload.append(
                        {
                            "bed_id": bed_id,
                            "case_id": src.case_id,
                            "sim_t": t,
                            "vitals": vitals,
                            "alerts": alerts.evaluate(vitals),
                        }
                    )
                await ws.send_json({"type": "tick", "beds": payload})
                last_t = t
            elapsed = time.monotonic() - frame_start
            await asyncio.sleep(max(0.05, REAL_TICK_SEC - elapsed))
    except WebSocketDisconnect:
        log.info("client disconnected")


@app.websocket("/ws/waveform/{bed_id}")
async def ws_waveform(ws: WebSocket, bed_id: str):
    if bed_id not in beds:
        await ws.close(code=4404)
        return
    await ws.accept()
    src = beds[bed_id]
    src.ensure_waveform_loaded()
    prev_t = sim_t
    try:
        while True:
            frame_start = time.monotonic()
            t = sim_t
            if t != prev_t:
                window = src.waveform_window(prev_t, t)
                await ws.send_json({"type": "wave", "bed_id": bed_id, "sim_t": t, **window})
                prev_t = t
            elapsed = time.monotonic() - frame_start
            await asyncio.sleep(max(0.05, REAL_TICK_SEC - elapsed))
    except WebSocketDisconnect:
        log.info("waveform client disconnected for %s", bed_id)
