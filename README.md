# ICU Dashboard Analogue (patient-history-tracking)

An open-source stand-in for commercial ICU-aggregation dashboards (e.g. vTitan's Jeevantra/IntelliICU,
Etiometry, Dozee, AcuteCare.ai CritIS): a device-integration layer that streams live vitals into a
multi-bed React dashboard with threshold-based alarms. Around the vitals feed it adds a synthetic
ABHA-style patient ID card, a continuity-of-care timeline, simulated insurance connect, prescription
and lab-report OCR with human review, and an auto-generated discharge summary. Domain: critical-care
informatics (India/ABDM-flavoured). Outputs: a live web dashboard and a printable synthetic discharge
summary (HTML).

> Status: research-only prototype. Not a medical device, not validated for clinical use; alarm thresholds in
> `backend/app/alerts.py` are illustrative defaults, not clinically reviewed limits. Vitals come from VitalDB
> (CC BY-NC-SA 4.0); patient names, ABHA numbers, insurers and claims are all invented. See
> [docs/data-and-licensing.md](docs/data-and-licensing.md).

> New here? [How to use this repo with AI (Claude, Gemini, ChatGPT)](HOW_TO_USE_WITH_AI.md).

## What it does
- Replays real, de-identified bedside-monitor numerics (HR, SpO2, NIBP, RR, Temp) from 6 VitalDB surgical cases
  plus a "Bed-DEMO" fast-cycle bed, at 4x speed on a 1-second tick, over a WebSocket (`/ws/vitals`).
- Evaluates threshold alarms (warning/critical) per vital and shows colour-coded bed tiles with sparklines
  and lazily loaded ECG/PLETH waveforms.
- Carries a synthetic ABHA-style ID card per bed and an append-only health-record timeline (200 events per
  patient) that other features write into.
- Digitizes prescriptions and lab reports with local Tesseract OCR; nothing is trusted until a reviewer
  approves (optionally correcting) each candidate.
- Simulates insurance eligibility on admission and a claim on discharge; compiles a per-encounter discharge
  summary (JSON and a printable, bannered HTML document).
- Persists state in SQLite so a restart resumes the same session (sim clock, queues, summaries).

## Quick start
Tesseract must be installed as a system binary (pip only installs the Python wrapper):
`brew install tesseract` (macOS; see the Tesseract repo for other platforms).

```bash
git clone https://github.com/herrrickshaw/patient-history-tracking.git
cd patient-history-tracking

# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8710

# frontend (separate terminal)
cd frontend
npm install
npm run dev -- --port 5273
```

Open http://localhost:5273. The backend allows CORS from `localhost:5273` / `127.0.0.1:5273` only.

## How it works
```
VitalDB open dataset --(vitaldb lib, no credentials)--> backend (FastAPI)
backend --(WebSocket /ws/vitals, REST /api/beds/...)--> frontend (React + Vite)
```

| Stage | Module | Output |
|---|---|---|
| Load cases, replay numerics | `backend/app/vitals_source.py` | per-bed vitals series (plausibility-masked temperature) |
| Threshold alarms | `backend/app/alerts.py` | alert dicts (`warning` / `critical`) |
| Synthetic identity | `backend/app/patient_identity.py` | name + 14-digit ABHA-style ID from the case id; real age/sex/dept/procedure from VitalDB metadata |
| Timeline | `backend/app/health_record.py` | per-patient events (admission, alerts, meds, insurance, OCR, discharge) |
| Orders | `backend/app/prescriptions.py` | compressed-schedule demo medication orders |
| Insurance | `backend/app/insurance_connect.py` | simulated eligibility check and claim |
| OCR + review queue | `backend/app/prescription_ocr.py`, `lab_ocr.py`, endpoints in `main.py` | pending candidates, approved orders/lab results |
| Discharge summary | `backend/app/discharge_summary.py` | JSON + printable HTML |
| Persistence | `backend/app/db.py` | SQLite (stdlib `sqlite3`, WAL, no ORM) in `backend/data/` |

Design decisions: SQLite behind one process, matching the repo's plain style, instead of Postgres (see
[docs/persistence.md](docs/persistence.md)); local Tesseract so no image leaves the machine; every OCR
result is a candidate that a human must approve; the fast-cycle bed shortens only the encounter length
(40 sim-seconds) while vitals keep playing from real data. Per-feature detail is in
[docs/features.md](docs/features.md).

## Repository layout
| Path | Purpose |
|---|---|
| `backend/app/` | FastAPI app and domain modules (table above) |
| `backend/tests/` | pytest suite (alerts, OCR parsers, db, OCR review API; `vitaldb` is stubbed, no network) |
| `frontend/src/` | React components: bed grid (`App.jsx`, `PatientTile.jsx`), detail view (`PatientDetail.jsx`), ID/insurance cards, `HealthTimeline.jsx`, OCR panels, `DischargeSummaryPanel.jsx`, `WaveformCanvas.jsx` |
| `docs/` | Long-form detail moved out of the README (features, persistence, licensing, vendor research) |
| `graphify-out/` | Generated knowledge-graph output (tooling artefact, not source) |
| `backend/data/` | Runtime SQLite files, gitignored |

## Data sources
| Source | What is taken | Access route | Licence / caveat |
|---|---|---|---|
| [VitalDB](https://vitaldb.net/dataset/) (Seoul National University Hospital) | de-identified surgical-case vitals, waveforms and clinical metadata | `vitaldb` Python library at runtime; nothing is bundled | CC BY-NC-SA 4.0 plus a Data Use Agreement (no re-identification). Cite Lee HC et al., Sci Data 2022;9(1):279, [doi:10.1038/s41597-022-01411-5](https://doi.org/10.1038/s41597-022-01411-5) |

[MIMIC-IV Waveform DB](https://physionet.org/content/mimic4wdb/) is not used; it needs PhysioNet credentialing.
See [docs/data-and-licensing.md](docs/data-and-licensing.md) for how to swap it in.

## Configuration
No environment variables and no secrets are needed. Constants live in `backend/app/main.py`
(`NUM_BEDS = 6`, `REAL_TICK_SEC = 1.0`, `SIM_SECONDS_PER_TICK = 4`, `DEMO_ENCOUNTER_SIM_SEC = 40`) and
`backend/app/alerts.py` (`RULES`). The database path is `backend/data/app.db`.

## Testing
```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cd .. && ruff check . && pytest -q
cd frontend && npm ci && npm run lint && npm run build
```
Python 3.10+ is required to run the backend. CI (`.github/workflows/ci.yml`) runs the same checks.

## Limitations and known issues
- Prototype only; thresholds are not clinically reviewed.
- Tesseract misreads: in testing a typed image still turned a 650mg dose into 850mg, and handwriting is
  worse. This is why nothing from OCR is auto-trusted.
- Only the latest encounter's discharge summary is kept per bed; on the fast-cycle bed each discharge
  overwrites the previous one.
- Single-process SQLite; no auth, containerization, device-integration engine, ML inference, mobile clients
  or observability (see [docs/vendor-landscape.md](docs/vendor-landscape.md)).
- The "Real-world context" vendor research (ABDM, EMR stacks, insurers, competitors) is background, was not
  re-verified in the 2026-11 refactor, and the app does not connect to any of those systems.
- `npm run lint` reports 4 existing warnings (react-hooks/refs) that have not been changed.

## Related repositories
None required. Reference projects borrowed from: [mdpnp/mdpnp (OpenICE)](https://github.com/mdpnp/mdpnp),
[Farhan-ux/icu-patient-monitor](https://github.com/Farhan-ux/icu-patient-monitor),
[hl7-be/patient-monitoring](https://github.com/hl7-be/patient-monitoring).

## Licence
MIT, see `LICENSE`. VitalDB data is governed separately (see above).
