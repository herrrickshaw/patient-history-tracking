"""ICU dashboard analogue backend.

Streams real (de-identified) bedside-monitor vitals from VitalDB's open
dataset over a WebSocket, evaluates threshold alarms, and exposes a
small REST surface for the bed roster -- the software layer an
IntelliICU-style product puts on top of connected monitors, pumps, and
ventilators.
"""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import alerts, health_record, insurance_connect, patient_identity, vitals_source

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("icu-dashboard")

NUM_BEDS = 6
REAL_TICK_SEC = 1.0
SIM_SECONDS_PER_TICK = 4  # playback speed-up so a ~90min case cycles in a demo-friendly window

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
sim_t = 0


@app.on_event("startup")
def load_beds() -> None:
    case_ids = vitals_source.pick_case_ids(NUM_BEDS)
    labels = [chr(ord("A") + i) for i in range(NUM_BEDS)]
    for label, case_id in zip(labels, case_ids):
        bed_id = f"Bed-{label}"
        log.info("loading %s <- VitalDB case %s", bed_id, case_id)
        beds[bed_id] = vitals_source.BedSource(bed_id, case_id)
        identity = patient_identity.build_identity(bed_id, case_id)
        bed_identities[bed_id] = identity
        _admit(bed_id, identity, sim_t=0)


@app.on_event("startup")
async def start_clock() -> None:
    async def clock_loop():
        global sim_t
        last_alert_keys: dict[str, set[str]] = {bed_id: set() for bed_id in beds}
        last_cycle: dict[str, int] = {bed_id: 0 for bed_id in beds}
        while True:
            await asyncio.sleep(REAL_TICK_SEC)
            sim_t += SIM_SECONDS_PER_TICK
            _record_events(sim_t, last_alert_keys, last_cycle)

    asyncio.create_task(clock_loop())


def _admit(bed_id: str, identity: dict, sim_t: int) -> None:
    health_record.push_event(
        identity["abha_id"], "admission", source=bed_id, sim_t=sim_t,
        payload={"department": identity["department"], "procedure": identity["procedure"]},
    )
    eligibility = insurance_connect.check_eligibility(identity["abha_id"])
    health_record.push_event(
        identity["abha_id"], "insurance_eligibility_checked", source=bed_id, sim_t=sim_t, payload=eligibility,
    )


def _discharge(bed_id: str, identity: dict, sim_t: int) -> None:
    health_record.push_event(identity["abha_id"], "discharge", source=bed_id, sim_t=sim_t, payload={})
    claim = insurance_connect.submit_claim(
        identity["abha_id"], {"department": identity["department"], "procedure": identity["procedure"]},
    )
    health_record.push_event(
        identity["abha_id"], "insurance_claim_submitted", source=bed_id, sim_t=sim_t, payload=claim,
    )


def _record_events(t: int, last_alert_keys: dict[str, set[str]], last_cycle: dict[str, int]) -> None:
    for bed_id, src in beds.items():
        identity = bed_identities[bed_id]
        abha_id = identity["abha_id"]

        cycle = t // src.length
        if cycle > last_cycle[bed_id]:
            _discharge(bed_id, identity, t)
            _admit(bed_id, identity, t)
            last_cycle[bed_id] = cycle
            last_alert_keys[bed_id] = set()  # new encounter, previous alarms don't carry over

        vitals = src.tick(t)
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
        {"bed_id": bed_id, "source": f"VitalDB case #{src.case_id}", "length_sec": src.length}
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
