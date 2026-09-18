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
or credentialing gate, unlike PhysioNet's MIMIC-IV below). Numerics
(HR, SpO2, NIBP, RR, Temp) are replayed at 4x speed on a 1-second
tick.

## VitalDB data attribution & license

This app fetches VitalDB case data live via the `vitaldb` Python
library at runtime — it doesn't bundle or redistribute any VitalDB
files. That data is governed entirely separately from this repo's own
code license (MIT, see `LICENSE`):

- **License**: VitalDB's open dataset is released by the VitalDB team
  under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0
  International (CC BY-NC-SA 4.0)**, alongside a formal Data Use
  Agreement (see the "Data Use Agreement" section at
  https://vitaldb.net/dataset/) covering research/development use, a
  ban on attempting patient re-identification, and restrictions on
  further disclosure — it applies to anyone who accesses the data
  (there's just no login/click-through gate enforcing it, unlike
  PhysioNet's credentialed datasets).
- **Citation** (required by the license): Lee HC, Park Y, Yoon SB,
  Yang SM, Park D, Jung CW. *VitalDB, a high-fidelity multi-parameter
  vital signs database in surgical patients.* Sci Data. 2022 Jun
  8;9(1):279. doi:
  [10.1038/s41597-022-01411-5](https://doi.org/10.1038/s41597-022-01411-5).
  PMID: 35676300; PMCID: PMC9178032.
- If you build on this repo for anything beyond your own research/
  development use, read VitalDB's Data Use Agreement yourself at
  https://vitaldb.net/dataset/ — this README is a summary, not a
  substitute for it.

## Swapping in MIMIC-IV / real ICU data later

[MIMIC-IV Waveform DB](https://physionet.org/content/mimic4wdb/) has
higher-fidelity ICU (not just OR) data, but requires completing
PhysioNet's CITI "Data or Specimens Only Research" training and
accepting a per-dataset Data Use Agreement — that's a step only you
can do, at https://physionet.org. Once credentialed, swap
`backend/app/vitals_source.py`'s VitalDB loader for a MIMIC-IV
waveform reader; the bed/tick/alert interfaces don't need to change.

## ABHA-style ID card

Every bed carries a patient identity card (`backend/app/patient_identity.py`,
rendered by `frontend/src/IdCard.jsx`) patterned after India's ABHA
(Ayushman Bharat Health Account) — the linkage a real Indian hospital
system shows on a patient's chart, and the ID everything else in this
app (insurance, prescriptions, lab results, the timeline) is keyed by.

Everything on the card is either real-but-anonymous or entirely
invented, and it's split deliberately:

- **Real**: age, sex, department, procedure, diagnosis, and ASA class
  come straight from VitalDB's own de-identified clinical metadata for
  that case (`vitaldb.load_clinical_data`) — genuine (if anonymous)
  surgical case data, not fabricated.
- **Invented**: the patient's name and the 14-digit ABHA-style number
  (`XX-XXXX-XXXX-XXXX`) don't exist in VitalDB at all — a real patient
  name and national health ID obviously aren't part of an open
  research dataset — so both are generated deterministically from the
  case id purely so the card has something to display.

The card carries a permanent "DEMO ID — not a real ABHA record" banner
and disclaimer; nothing here calls, mimics, or could be confused with
the real ABHA/NHA API.

## Real-world context: the ABHA vendor ecosystem

Background for anyone comparing this demo's ID card to how ABHA
actually works — reference material, not something the app implements
or connects to.

The real ABHA number is a 14-digit ID (the same `XX-XXXX-XXXX-XXXX`
shape this app's synthetic card imitates), but a citizen's day-to-day
identifier is usually an **ABHA address** instead — a
`username@handle` form (e.g. `xyz@abdm`), where the suffix names which
**Consent Manager** brokers that person's data-sharing consent. As of
2026, the National Health Authority (NHA) reports 380M+ ABHA IDs
created, 480,000+ facilities in the Health Facility Registry, and
950,000+ doctors in the Healthcare Professionals Registry.

Three distinct roles make up the vendor ecosystem around that ID,
and a single company can register as more than one:

- **PHR apps** (Personal Health Records) — the apps citizens actually
  use to create an ABHA address and view their own records. The
  NHA-run `ABHA` app itself is one; PHR apps that store patient health
  data must separately register with NHA.
- **HIP** (Health Information Provider) — hospitals, labs, clinics,
  pharmacies that hold and expose a patient's records into the
  network.
- **HIU** (Health Information User) — apps that request access to
  those records, with the patient's consent.
- **Consent Manager / HIE-CM** — the licensed broker that orchestrates
  consent between HIPs and HIUs (the ABDM Gateway can itself act as
  the default one, the `@abdm` suffix).

**[Eka.Care](https://www.eka.care/services/abdm-enabling-ecosystems)**
was one of the first private platforms to register as *both* a HIP and
an HIU. The government has claimed roughly 800 companies onboarded
onto ABDM overall, though no single public, itemized registry of every
licensed Consent Manager turned up in research for this section — take
that count as a government-stated figure, not something independently
verified here.

One easy mix-up worth flagging: India's 2023 Digital Personal Data
Protection Act (DPDPA) introduces a *separate* "Consent Manager"
concept, licensed by the Data Protection Board across all sectors, not
just health — as of late 2026 its registration window had only just
opened, so it's a different (and much newer) thing from the
already-operating ABDM/health Consent Managers described above.

## Health record timeline

`backend/app/health_record.py` is the continuity-of-care record every
other feature writes into: a per-patient, append-only timeline of
events (admission, discharge, alerts raised/resolved, vitals
snapshots, medications administered, insurance eligibility/claims, OCR
digitize/approve/reject), keyed by the same ABHA ID as the ID card and
capped at 200 events per patient.

It's the same pattern behind two real systems, used only as a design
reference — this module doesn't call, authenticate against, or claim
to be either:

- **India's ABDM/ABHA**: providers push encounter data into a health
  record linked by ABHA number, retrievable across facilities.
- **Germany's gematik Telematikinfrastruktur / elektronische
  Patientenakte (ePA)**: statutory insurers keep a continuity-of-care
  record that updates as care happens across providers.

Rendered as the "Health information history" panel
(`frontend/src/HealthTimeline.jsx`) in the patient detail view, and
it's also where several other features get their data *from* rather
than maintaining their own parallel store — e.g. approved lab results
(`GET /api/beds/{bed_id}/labs`) and each encounter's alert/medication
history in the discharge summary are both derived by filtering this
timeline, not tracked separately.

## Fast-cycle demo bed

`Bed-DEMO` (badged "FAST-CYCLE DEMO" in the grid) plays back a real
VitalDB case like every other bed, but its admission-to-discharge
**encounter length** is decoupled from that case's actual physiological
data length: `backend/app/vitals_source.py`'s `BedSource` takes an
optional `encounter_length` override (40 sim-seconds, ≈10 real seconds
at 4x playback) instead of defaulting to the full case duration.

The vitals themselves keep playing continuously off the real data —
only the admission/discharge/insurance/prescription cycle is
compressed. That's what makes it possible to actually *watch* a full
discharge → insurance claim → re-admission → fresh prescriptions cycle
inside the same session, instead of waiting out a ~15-real-minute
natural case wrap like the other six beds.

## Insurance connect (simulated)

`backend/app/insurance_connect.py` fires an eligibility check on every
admission and a claim submission on every discharge, both keyed by the
same synthetic ABHA ID as everything else in the patient's record.

It's patterned after two real systems, used only as a design
reference — nothing here calls either one:

- **Germany's gematik Telematikinfrastruktur (TI)**: a statutory
  insurer electronically confirms coverage when a patient's eGK
  (health card) is read at admission, and receives the billing claim
  at discharge.
- **India's ABDM Health Claims Exchange (HCX)**: standardises
  eligibility checks and claim submission between providers and
  payers, linked by the patient's ABHA number.

Insurer names (`Yojana Mutual Health`, `Concordia Health Assurance`,
etc.), policy numbers, eligibility status, and claim amounts/decisions
are all invented deterministically from the ABHA ID — no real insurer,
payer network, or claims clearinghouse is contacted, and no real
financial transaction occurs. Surfaced in the UI as the "Simulated
Insurance Connect" card and folded into the same health-record
timeline as every other encounter event.

## Real-world context: the ABDM vendor ecosystem

Background for anyone comparing this demo to what actually exists in
India — this section is reference material, not something the app
implements or connects to.

Unlike most countries, India's *public* hospital system mostly runs
software **built by government bodies themselves**, not bought from
private EMR vendors:

- **[e-Hospital](https://www.nic.gov.in/project/ehospital/)**, built
  by NIC (National Informatics Centre, a government department under
  MeitY), is the default HMIS across most government hospitals.
- **[eSushrut](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2156603&reg=3&lang=2)**,
  built by C-DAC (a government R&D body), runs at all 17 AIIMS and
  4,000+ facilities; a lighter `eSushrut@Clinic` variant targets
  small/medium providers under ABDM.
- **[CoWIN](https://www.undp.org/india/projects/winning-over-covid-cowin)**,
  India's COVID vaccination platform, was built the same way — an
  in-house government team (drawing on the Aadhaar/UPI/DigiLocker
  "digital public goods" playbook) with UNDP support, not a private
  vendor contract.

Private companies participate in the ecosystem this app's insurance
connect and OCR features are patterned after, in two different ways:

- **Selling EMR/HMIS software to *private* hospitals** — the market
  this repo's other reference projects and comparisons target:
  Healthray, HealthPlix, KareXpert, and (with real international
  export, unlike most of that list) [Attune Technologies](https://ehealth.eletsonline.com/2015/10/attune-software-technology-expands-beyond-india/),
  which sells its own cloud EMR across 15 countries in the Middle
  East, Africa, and Southeast Asia. ABDM-certified vendor lists (e.g.
  [SIDH's network](https://www.sidh.co.in/emrvendors)) track which of
  these meet the government's interoperability requirements.
- **Getting paid directly by the government** as ABDM ecosystem
  participants, via the National Health Authority's [Digital Health
  Incentives Scheme (DHIS)](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=1945911&reg=48&lang=2),
  which pays a per-transaction incentive for linking hospitals, labs,
  and pharmacies into ABDM. Named top performers include **Eka.Care
  (Orbi Health)**, **Bajaj Finserv**, and **Paytm** — notably, two of
  those are fintech/consumer companies rather than traditional
  health-IT vendors, pulled in by the incentive structure itself.

The Health Claims Exchange (HCX) piece this app's `insurance_connect.py`
is patterned after is the standardisation layer for that second
category — the eligibility-check/claim-submission protocol between
providers and payers, linked by ABHA number.

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

## Lab report OCR digitization

Same pipeline and the same non-negotiable review discipline, applied
to lab reports instead of prescriptions
(`backend/app/lab_ocr.py`). Testing it surfaced an even sharper
example of why: a typed test report round-tripped through Tesseract
and **lost every decimal point** — `13.5 g/dL` came back as `135`,
`0.9 mg/dL` as `09`, and `12.0-15.5` as `120-155`. Because the
(wrong) reference range and the (wrong) value were internally
consistent, the auto-computed flag looked plausible too — exactly the
kind of silent, easy-to-miss failure a review step exists to catch.

1. `POST /api/beds/{bed_id}/labs/ocr` extracts text, then a regex
   parser matches each line against a list of recognized analyte names
   (Hemoglobin, WBC, Creatinine, Sodium, Glucose, etc.) and pulls
   `value` / `unit` / `reference_range`; lines that don't mention a
   recognized test are skipped so report headers/footers don't become
   spurious results. A `flag` (`high`/`low`/`normal`) is computed by
   comparing the extracted value against the extracted range.
2. Every candidate lands in a pending-review queue
   (`GET /api/beds/{bed_id}/labs/pending`) — never directly recorded
   as a result.
3. `POST .../pending/{item_id}/approve` takes the same kind of
   correction override as prescriptions, so a reviewer can fix a
   misread value/unit/range before it's recorded.
   `POST .../pending/{item_id}/reject` discards a candidate.
4. Approved results are derived straight from the patient's
   health-record timeline (`GET /api/beds/{bed_id}/labs` filters for
   `lab_result_approved` events — no separate results store) and are
   included in the discharge summary, both the JSON payload and the
   printable HTML document.

Frontend: `frontend/src/LabOCR.jsx` (upload + review) and
`frontend/src/LabResults.jsx` (approved results table), inside the
patient detail view next to the prescription tracker.

## Discharge summary generator

At the moment a bed discharges — naturally, or every ~10s on the
fast-cycle demo bed — `backend/app/discharge_summary.py` compiles
everything that happened during that one encounter into a single
document:

- Vitals min/max/last, tracked continuously through the encounter
  (`main.py`'s `_update_vitals_accum`, reset on each admission) rather
  than sampled from the periodic snapshots.
- Every `alert_raised` and `medication_administered` event whose
  `sim_t` falls inside the encounter's admission→discharge window,
  filtered straight out of the health-record timeline.
- Any `lab_result_approved` events from the same window — so a lab
  result only makes it into the summary once a human has reviewed and
  approved the OCR candidate, never straight from the pending queue.
- The insurance-connect claim submitted at that same discharge.

It's exposed two ways from the same underlying summary:

- `GET /api/beds/{bed_id}/discharge-summary` — JSON, rendered inline
  as the "Discharge summary" panel (`frontend/src/DischargeSummaryPanel.jsx`)
  in the patient detail view.
- `GET /api/beds/{bed_id}/discharge-summary.html` — a self-contained,
  printable HTML document (linked from that panel as "Open printable
  document"), with a mandatory red **SYNTHETIC DEMO DOCUMENT — NOT A
  REAL DISCHARGE SUMMARY — NOT FOR CLINICAL USE** banner and the same
  disclaimer repeated at the foot of the document, so it can't be
  mistaken for the real thing even if printed or saved on its own.

Only the *latest* encounter's summary is kept per bed
(`discharge_summary.latest()`) — on the fast-cycle demo bed in
particular, each new discharge overwrites what came before.

## Swapping in a commercial OCR SDK later

Local Tesseract is free and needs no credentials, but it's a generic
OCR engine with no idea it's looking at a prescription or a lab
report — real handwriting accuracy suffers accordingly (see the
misreads documented above). A document-scanning SDK purpose-built for
this ([Kaagaz](https://kaagaz.app/scanning-sdk) is one Indian example,
among others such as Google Cloud Vision or AWS Textract) would likely
do meaningfully better, at the cost of integration effort this repo
doesn't include:

- Kaagaz's SDK is mobile-native (Android/iOS, on-device processing)
  and requires emailing their team for access and a commercial
  agreement — not something obtainable or wireable in from here.
- Cloud OCR services (Vision/Textract/Form Recognizer) need an API key
  and send image data off-device, a real privacy tradeoff for medical
  documents that local Tesseract avoids.

If you get access to one of these, the integration point is the same
shape either way: swap `prescription_ocr.extract_text()` /
`lab_ocr.extract_text()` for a call to the new service; everything
downstream (parsing, the pending-review queue, correction-on-approve)
doesn't need to change.

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
