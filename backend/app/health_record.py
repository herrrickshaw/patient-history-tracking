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
system -- it is a local demo analogue only. No real insurer,
government health-ID registry, or patient data is involved.

Backed by SQLite (backend/app/db.py) so the timeline survives a
server restart, unlike the plain in-memory dict this module used to
keep.
"""
from __future__ import annotations

from . import db

DISCLAIMER = (
    "Simulated health information exchange, patterned after ABHA (India) and "
    "gematik's Telematikinfrastruktur/ePA (Germany) continuity-of-care model. "
    "Not connected to any real insurer, government registry, or health-ID system."
)


def push_event(abha_id: str, event_type: str, source: str, sim_t: int, payload: dict) -> None:
    db.push_health_event(abha_id, event_type, source, sim_t, payload)


def get_timeline(abha_id: str) -> list[dict]:
    return db.get_health_timeline(abha_id)
