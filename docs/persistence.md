# Persistence layer

`backend/app/db.py` — plain standard-library `sqlite3`, no ORM,
matching the rest of this codebase's style. Added because every other
piece of state used to live in module-level Python dicts, so
restarting the server erased every patient, timeline event, and
discharge summary; that's now fixed.

- One connection (WAL mode) shared by the whole app; every write
  commits immediately — this app's write volume (a handful of events
  per sim-second) is nowhere near where that would matter.
- Tables: `health_events` (the continuity-of-care timeline),
  `prescriptions`, `ocr_pending` (the review queue shared by both OCR
  features, discriminated by a `kind` column), `insurance_records`,
  `discharge_summaries`, `bed_runtime` (per-bed admission time + the
  running vitals min/max/last accumulator), and `app_state` (currently
  just the sim-time clock, so a restart resumes playback instead of
  rewinding to t=0).
- `health_record.py`, `insurance_connect.py`, and `discharge_summary.py`
  now read/write through `db.py` internally — their own function
  signatures (`push_event`, `get_timeline`, `check_eligibility`,
  `submit_claim`, `build`, `latest`, ...) didn't change, so every REST
  endpoint that calls them needed no changes at all.
- On startup, each bed checks whether it already has persisted
  prescriptions; if so it resumes that session in place rather than
  re-admitting over it (which would wipe the existing state and log a
  spurious second admission). Verified this directly: restarted the
  server mid-session and confirmed the sim clock resumed at its exact
  prior value, an in-review OCR candidate was still in the pending
  queue with the same id, and approving it afterward worked
  identically to before the restart.
- `backend/data/` (the `.db`/`-wal`/`-shm` files) is gitignored — it's
  local runtime state, not something to commit.

Still SQLite behind one process, not the Postgres/MySQL + horizontal
scaling real companies run — see the infrastructure-gap section near
the end of this README for what's still missing and why.

