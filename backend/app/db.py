"""SQLite persistence layer.

Replaces the plain-Python-dict state every other module used to keep
in memory (health_record._records, insurance_connect._records,
discharge_summary._summaries, and main.py's bed_* dicts) -- until now,
restarting the server erased every patient, timeline event, and
discharge summary. This is the fix: real, standard-library sqlite3,
no ORM, matching the rest of this codebase's plain-function style.

One connection, WAL mode (safe for the single-process FastAPI server
this app runs as), foreign keys off (SQLite default) since nothing
here needs cascading deletes. Every write commits immediately -- this
app's write volume (a handful of events per sim-second) is nowhere
near where that would matter.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS bed_runtime (
    bed_id TEXT PRIMARY KEY,
    admit_t INTEGER NOT NULL DEFAULT 0,
    vitals_accum_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS health_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    abha_id TEXT NOT NULL,
    bed_id TEXT NOT NULL,
    sim_t INTEGER NOT NULL,
    wall_time REAL NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_health_events_abha ON health_events(abha_id, id);

CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bed_id TEXT NOT NULL,
    drug TEXT,
    dose TEXT,
    route TEXT,
    frequency_sim_sec INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    next_due INTEGER,
    source TEXT NOT NULL DEFAULT 'standard'
);
CREATE INDEX IF NOT EXISTS idx_prescriptions_bed ON prescriptions(bed_id);

CREATE TABLE IF NOT EXISTS ocr_pending (
    id TEXT PRIMARY KEY,
    bed_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ocr_pending_bed_kind ON ocr_pending(bed_id, kind);

CREATE TABLE IF NOT EXISTS insurance_records (
    abha_id TEXT PRIMARY KEY,
    insurer TEXT,
    policy_number TEXT,
    eligibility_status TEXT,
    authorization_ref TEXT,
    checks_count INTEGER NOT NULL DEFAULT 0,
    claims_count INTEGER NOT NULL DEFAULT 0,
    last_claim_json TEXT
);

CREATE TABLE IF NOT EXISTS discharge_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    abha_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    summary_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_discharge_summaries_abha ON discharge_summaries(abha_id, id);
"""


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


# ---- app_state (global key/value, used for the sim-time clock) ----

def get_state(key: str, default: str | None = None) -> str | None:
    row = get_conn().execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_state(key: str, value: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO app_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


# ---- bed_runtime (admission time + running vitals accumulator per bed) ----

def get_bed_runtime(bed_id: str) -> dict:
    row = get_conn().execute("SELECT admit_t, vitals_accum_json FROM bed_runtime WHERE bed_id = ?", (bed_id,)).fetchone()
    if row is None:
        return {"admit_t": 0, "vitals_accum": {}}
    return {"admit_t": row["admit_t"], "vitals_accum": json.loads(row["vitals_accum_json"])}


def set_bed_admit_t(bed_id: str, admit_t: int) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO bed_runtime (bed_id, admit_t, vitals_accum_json) VALUES (?, ?, '{}')
           ON CONFLICT(bed_id) DO UPDATE SET admit_t = excluded.admit_t, vitals_accum_json = '{}'""",
        (bed_id, admit_t),
    )
    conn.commit()


def set_bed_vitals_accum(bed_id: str, accum: dict) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO bed_runtime (bed_id, admit_t, vitals_accum_json) VALUES (?, 0, ?)
           ON CONFLICT(bed_id) DO UPDATE SET vitals_accum_json = excluded.vitals_accum_json""",
        (bed_id, json.dumps(accum)),
    )
    conn.commit()


# ---- health_events (continuity-of-care timeline) ----

MAX_EVENTS_PER_PATIENT = 200


def push_health_event(abha_id: str, event_type: str, source: str, sim_t: int, payload: dict) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO health_events (abha_id, bed_id, sim_t, wall_time, event_type, payload_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (abha_id, source, sim_t, time.time(), event_type, json.dumps(payload)),
    )
    conn.execute(
        """DELETE FROM health_events WHERE abha_id = ? AND id NOT IN (
               SELECT id FROM health_events WHERE abha_id = ? ORDER BY id DESC LIMIT ?
           )""",
        (abha_id, abha_id, MAX_EVENTS_PER_PATIENT),
    )
    conn.commit()


def get_health_timeline(abha_id: str) -> list[dict]:
    rows = get_conn().execute(
        "SELECT sim_t, wall_time, event_type, bed_id, payload_json FROM health_events "
        "WHERE abha_id = ? ORDER BY id DESC",
        (abha_id,),
    ).fetchall()
    return [
        {
            "wall_time": r["wall_time"],
            "sim_t": r["sim_t"],
            "type": r["event_type"],
            "source": r["bed_id"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


# ---- prescriptions ----

def insert_prescriptions(bed_id: str, orders: list[dict]) -> None:
    conn = get_conn()
    conn.executemany(
        "INSERT INTO prescriptions (bed_id, drug, dose, route, frequency_sim_sec, status, next_due, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (bed_id, o["drug"], o["dose"], o["route"], o["frequency_sim_sec"], o["status"], o["next_due"], o.get("source", "standard"))
            for o in orders
        ],
    )
    conn.commit()


def _prescription_row_to_dict(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "drug": r["drug"],
        "dose": r["dose"],
        "route": r["route"],
        "frequency_sim_sec": r["frequency_sim_sec"],
        "status": r["status"],
        "next_due": r["next_due"],
        "source": r["source"],
    }


def get_prescriptions(bed_id: str) -> list[dict]:
    rows = get_conn().execute("SELECT * FROM prescriptions WHERE bed_id = ? ORDER BY id", (bed_id,)).fetchall()
    return [_prescription_row_to_dict(r) for r in rows]


def get_active_prescriptions(bed_id: str) -> list[dict]:
    rows = get_conn().execute(
        "SELECT * FROM prescriptions WHERE bed_id = ? AND status = 'active' ORDER BY id", (bed_id,)
    ).fetchall()
    return [_prescription_row_to_dict(r) for r in rows]


def discontinue_prescriptions(bed_id: str) -> None:
    conn = get_conn()
    conn.execute("UPDATE prescriptions SET status = 'discontinued' WHERE bed_id = ? AND status = 'active'", (bed_id,))
    conn.commit()


def mark_prescription_administered(prescription_id: int, next_due: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE prescriptions SET next_due = ? WHERE id = ?", (next_due, prescription_id))
    conn.commit()


# ---- ocr_pending (candidate queue shared by prescription + lab OCR) ----

def add_pending(item_id: str, bed_id: str, kind: str, payload: dict) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO ocr_pending (id, bed_id, kind, payload_json) VALUES (?, ?, ?, ?)",
        (item_id, bed_id, kind, json.dumps(payload)),
    )
    conn.commit()


def get_pending(bed_id: str, kind: str) -> list[dict]:
    rows = get_conn().execute(
        "SELECT id, payload_json FROM ocr_pending WHERE bed_id = ? AND kind = ? ORDER BY rowid", (bed_id, kind)
    ).fetchall()
    out = []
    for r in rows:
        item = json.loads(r["payload_json"])
        item["id"] = r["id"]
        out.append(item)
    return out


def get_pending_item(item_id: str, kind: str) -> dict | None:
    row = get_conn().execute(
        "SELECT payload_json FROM ocr_pending WHERE id = ? AND kind = ?", (item_id, kind)
    ).fetchone()
    if row is None:
        return None
    item = json.loads(row["payload_json"])
    item["id"] = item_id
    return item


def remove_pending(item_id: str) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM ocr_pending WHERE id = ?", (item_id,))
    conn.commit()


# ---- insurance_records ----

def get_insurance_record(abha_id: str) -> dict | None:
    row = get_conn().execute("SELECT * FROM insurance_records WHERE abha_id = ?", (abha_id,)).fetchone()
    if row is None:
        return None
    return {
        "insurer": row["insurer"],
        "policy_number": row["policy_number"],
        "eligibility_status": row["eligibility_status"],
        "authorization_ref": row["authorization_ref"],
        "_checks": row["checks_count"],
        "_claims": row["claims_count"],
        "last_claim": json.loads(row["last_claim_json"]) if row["last_claim_json"] else None,
    }


def upsert_insurance_eligibility(abha_id: str, insurer: str, policy_number: str, status: str, auth_ref: str, checks: int) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO insurance_records (abha_id, insurer, policy_number, eligibility_status, authorization_ref, checks_count)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(abha_id) DO UPDATE SET
               insurer = excluded.insurer, policy_number = excluded.policy_number,
               eligibility_status = excluded.eligibility_status,
               authorization_ref = excluded.authorization_ref, checks_count = excluded.checks_count""",
        (abha_id, insurer, policy_number, status, auth_ref, checks),
    )
    conn.commit()


def upsert_insurance_claim(abha_id: str, insurer: str, policy_number: str, claim: dict, claims: int) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT INTO insurance_records (abha_id, insurer, policy_number, claims_count, last_claim_json)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(abha_id) DO UPDATE SET
               claims_count = excluded.claims_count, last_claim_json = excluded.last_claim_json""",
        (abha_id, insurer, policy_number, claims, json.dumps(claim)),
    )
    conn.commit()


# ---- discharge_summaries ----

def insert_discharge_summary(abha_id: str, generated_at: str, summary: dict) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO discharge_summaries (abha_id, generated_at, summary_json) VALUES (?, ?, ?)",
        (abha_id, generated_at, json.dumps(summary)),
    )
    conn.commit()


def latest_discharge_summary(abha_id: str) -> dict | None:
    row = get_conn().execute(
        "SELECT summary_json FROM discharge_summaries WHERE abha_id = ? ORDER BY id DESC LIMIT 1", (abha_id,)
    ).fetchone()
    return json.loads(row["summary_json"]) if row else None
