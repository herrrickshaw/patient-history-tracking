"""Continuity-of-care record: a per-patient timeline that care events get
pushed into as they happen, keyed by the patient's (synthetic) health ID.

This is the same pattern behind two real systems, used here only as a
design reference:
  - India's ABDM/ABHA: providers push encounter data into a health
    record linked by ABHA number, retrievable across facilities.
  - Germany's gematik Telematikinfrastruktur / elektronische
    Patientenakte (ePA): statutory insurers keep a continuity-of-care
    record that updates as care happens across providers.

This module does not call, authenticate against, or claim to be either
system -- it is an in-memory analogue for demo purposes only. No real
insurer, government health-ID registry, or patient data is involved.
"""
from __future__ import annotations

import time
from collections import defaultdict

DISCLAIMER = (
    "Simulated health information exchange, patterned after ABHA (India) and "
    "gematik's Telematikinfrastruktur/ePA (Germany) continuity-of-care model. "
    "Not connected to any real insurer, government registry, or health-ID system."
)

MAX_EVENTS_PER_PATIENT = 200

_records: dict[str, list[dict]] = defaultdict(list)


def push_event(abha_id: str, event_type: str, source: str, sim_t: int, payload: dict) -> None:
    events = _records[abha_id]
    events.append(
        {
            "wall_time": time.time(),
            "sim_t": sim_t,
            "type": event_type,
            "source": source,
            "payload": payload,
        }
    )
    if len(events) > MAX_EVENTS_PER_PATIENT:
        del events[: len(events) - MAX_EVENTS_PER_PATIENT]


def get_timeline(abha_id: str) -> list[dict]:
    return list(reversed(_records.get(abha_id, [])))
