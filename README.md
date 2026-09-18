# ICU Dashboard Analogue

An open-source stand-in for commercial ICU-aggregation dashboards
(e.g. vTitan's Jeevantra/IntelliICU, Etiometry, Dozee, AcuteCare.ai
CritIS): a device-integration layer that streams live vitals into a
multi-bed dashboard with threshold-based alarms.

Built as a learning/prototyping reference, not a medical device — see
[Status](#status) below.

## Architecture

```
VitalDB open dataset  --(vitaldb python lib, no credentials)-->  backend/
  backend (FastAPI)    --(WebSocket /ws/vitals)-->  frontend (React)
  - replays real, de-identified bedside-monitor numerics per "bed"
  - evaluates threshold alarm rules (backend/app/alerts.py)
frontend (React + Vite)
  - live bed grid, sparklines, colour-coded alarms
```

Six beds are loaded at startup, each backed by a different real
surgical case from [VitalDB](https://vitaldb.net) (Seoul National
University Hospital's open, de-identified vitals dataset — no login
or Data Use Agreement required). Numerics (HR, SpO2, NIBP, RR, Temp)
are replayed at 4x speed on a 1-second tick.

## Swapping in MIMIC-IV / real ICU data later

[MIMIC-IV Waveform DB](https://physionet.org/content/mimic4wdb/) has
higher-fidelity ICU (not just OR) data, but requires completing
PhysioNet's CITI "Data or Specimens Only Research" training and
accepting a per-dataset Data Use Agreement — that's a step only you
can do, at https://physionet.org. Once credentialed, swap
`backend/app/vitals_source.py`'s VitalDB loader for a MIMIC-IV
waveform reader; the bed/tick/alert interfaces don't need to change.

## Prescription OCR digitization

Upload a photo or scan of a written prescription and the backend
digitizes it with local [Tesseract](https://github.com/tesseract-ocr/tesseract)
OCR — no cloud OCR service, no API key, nothing leaves the machine.

Handwriting recognition is unreliable, and this isn't a hypothetical
concern: testing the pipeline against a plain typed image, Tesseract
still misread a dose (650mg came back as 850mg) and garbled a
frequency abbreviation. Because of that, **nothing extracted is
trusted automatically**:

1. `POST /api/beds/{bed_id}/prescriptions/ocr` (multipart file upload)
   runs OCR (`backend/app/prescription_ocr.py`), then a regex parser
   pulls a `drug` / `dose` / `route` / `frequency` candidate out of
   each line, mapping common abbreviations (`OD`/`BD`/`TDS`/`QID`/
   `HS`/`STAT`/`PRN`) to the existing compressed demo cadence.
2. Every candidate lands in a per-bed **pending-review queue**
   (`GET /api/beds/{bed_id}/prescriptions/pending`) — never directly
   in the active prescription list.
3. `POST .../pending/{item_id}/approve` accepts an optional JSON body
   overriding any field, so a reviewer can fix a misread before it
   becomes an order — plain accept/discard isn't enough review to be
   meaningful. `POST .../pending/{item_id}/reject` discards a
   candidate instead.
4. Approved orders enter the same `backend/app/prescriptions.py`
   lifecycle as any other order (administered on schedule, discharged
   with the encounter) and show an **OCR** badge in the prescription
   tracker. Every digitize/approve/reject is logged to the patient's
   health-record timeline.

Frontend: `frontend/src/PrescriptionOCR.jsx` (upload, raw-OCR-text
disclosure, editable per-candidate review card) inside the patient
detail view, next to the prescription tracker.

## Running locally

Tesseract must be installed as a system binary (pip only installs the
Python wrapper around it):

```bash
brew install tesseract   # macOS; see the Tesseract repo for other platforms
```

```bash
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

Open http://localhost:5273.

## Reference projects this borrows ideas from

- [mdpnp/mdpnp (OpenICE)](https://github.com/mdpnp/mdpnp) — open-source
  reference implementation of the AAMI 2700-1 Integrated Clinical
  Environment standard; the real precedent for device-interoperability
  layers like this one.
- [Farhan-ux/icu-patient-monitor](https://github.com/Farhan-ux/icu-patient-monitor) —
  single-bed monitor dashboard (waveforms, IV infusions, alarms).
- [hl7-be/patient-monitoring](https://github.com/hl7-be/patient-monitoring) —
  FHIR Implementation Guide for patient-monitoring resources, useful
  if this needs to standardize its data model later.

## Status

Prototype/demo only. Not validated for clinical use, not a medical
device, and the alarm thresholds in `backend/app/alerts.py` are
illustrative defaults, not clinically reviewed limits.
