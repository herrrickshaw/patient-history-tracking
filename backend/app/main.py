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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import alerts, vitals_source

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


@app.on_event("startup")
def load_beds() -> None:
    case_ids = vitals_source.pick_case_ids(NUM_BEDS)
    labels = [chr(ord("A") + i) for i in range(NUM_BEDS)]
    for label, case_id in zip(labels, case_ids):
        bed_id = f"Bed-{label}"
        log.info("loading %s <- VitalDB case %s", bed_id, case_id)
        beds[bed_id] = vitals_source.BedSource(bed_id, case_id)


@app.get("/api/beds")
def list_beds():
    return [
        {"bed_id": bed_id, "source": f"VitalDB case #{src.case_id}", "length_sec": src.length}
        for bed_id, src in beds.items()
    ]


@app.get("/api/health")
def health():
    return {"status": "ok", "beds_loaded": len(beds)}


@app.websocket("/ws/vitals")
async def ws_vitals(ws: WebSocket):
    await ws.accept()
    sim_t = 0
    try:
        while True:
            frame_start = time.monotonic()
            payload = []
            for bed_id, src in beds.items():
                vitals = src.tick(sim_t)
                payload.append(
                    {
                        "bed_id": bed_id,
                        "case_id": src.case_id,
                        "sim_t": sim_t,
                        "vitals": vitals,
                        "alerts": alerts.evaluate(vitals),
                    }
                )
            await ws.send_json({"type": "tick", "beds": payload})
            sim_t += SIM_SECONDS_PER_TICK
            elapsed = time.monotonic() - frame_start
            await asyncio.sleep(max(0.0, REAL_TICK_SEC - elapsed))
    except WebSocketDisconnect:
        log.info("client disconnected")
