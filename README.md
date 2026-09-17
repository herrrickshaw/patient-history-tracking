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

## Running locally

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
