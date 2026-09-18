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
an HIU. Its Bangalore job postings show a modern, coherent stack:
**Go, Python (Django/Flask)** on the backend, native **iOS/Android**
mobile, and **AWS + Terraform + Jenkins** for infra/DevOps — a single
startup stack, unlike the mixed or client-dependent ones found for
the EMR-export companies above. The government has claimed roughly
800 companies onboarded onto ABDM overall, though no single public,
itemized registry of every licensed Consent Manager turned up in
research for this section — take that count as a government-stated
figure, not something independently verified here.

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
  Bajaj Finserv Health's job postings show **Java** backend, **React
  + Node.js** full-stack, and **Angular + Ionic** hybrid mobile — but
  that's their general health-platform engineering stack, not a team
  specifically labeled "ABDM" or "DHIS," so treat it as indicative
  rather than exact. Paytm's health/insurance-specific stack couldn't
  be confirmed — searches surfaced only their general engineering job
  postings, nothing tied to their health/ABDM work specifically.

The Health Claims Exchange (HCX) piece this app's `insurance_connect.py`
is patterned after is the standardisation layer for that second
category — the eligibility-check/claim-submission protocol between
providers and payers, linked by ABHA number.

## Real-world context: Indian EMR export company tech stacks

Background on the Indian companies that actually export EMR/health-data
products abroad (as opposed to the mostly-domestic HMIS vendors and
the government-built systems in the section above) — checked via job
postings, continuing the same verification approach as the ICU
dashboard competitors section.

- **[Attune Technologies](https://ehealth.eletsonline.com/2015/10/attune-software-technology-expands-beyond-india/)**
  — the clear real-export case already named above: its own cloud
  EMR/HIS across 15 countries. Job postings point to a **Spring Boot**
  backend and **React** frontend; one Glassdoor employee review
  separately mentions a broader "Microsoft stack" being used
  internally — a softer, less specific signal than the job-posting
  detail, so treat that part as less certain.
- **[Innovaccer](https://innovaccer.com/careers/jobs)** — not a
  ground-up EMR (it integrates with and extends EHRs like Epic and
  Cerner rather than replacing them), but the biggest Indian-origin
  health-tech product selling into the US. Its Noida engineering job
  postings show a genuinely **polyglot** stack rather than one
  answer: some backend roles want **Python/Django/Flask +
  PostgreSQL**, others want **Java/Spring/Hibernate**; frontend roles
  split between **React.js** and (in more senior listings) **AngularJS**;
  cloud/platform roles are **AWS**-based, described as "distributed
  systems" work on their "healthcare intelligence cloud." Reads like a
  company whose product surface grew through several different teams
  or acquisitions rather than one single stack decision.
- **[CitiusTech](https://www.citiustech.com/careers/job-openings)** —
  not a product company at all here, worth remembering: an IT-services
  firm that implements and integrates *other* vendors' EMRs (Epic,
  etc.) for global clients. Its job postings are correspondingly
  scattered across whatever a given client engagement needs: **Java/
  Spring/Microservices**, a **MERN** (React + Node) track, even
  **PHP/Laravel** on some listings, plus **Elasticsearch**, **Hasura**,
  multi-cloud (**AWS/GCP/Azure**), and **Docker/Kubernetes**. That
  breadth isn't a red flag the way it might be for a product company —
  it's the expected shape for a consulting firm whose stack is really
  "whatever the client's stack is."

The pattern across all three mirrors the ICU-competitor section's
finding: a company that owns one product (Attune) converges on one
stack; a company integrating with many external systems (Innovaccer,
and especially the pure-services CitiusTech) shows a stack that's
either genuinely mixed or entirely client-dependent.

## Real-world context: insurance connect vendors

Background for anyone comparing this demo's `insurance_connect.py`
(the eligibility-check-on-admission, claim-on-discharge cycle) to what
already exists — reference material, not something the app implements
or connects to.

**India (NHCX):** the HCX layer mentioned above has a name — the
**National Health Claims Exchange (NHCX)**, built by NHA in
consultation with the insurance regulator (IRDAI) under ABDM, live
since June 2024. As of May 2026, NHA reports **160 integrators and
12,600+ hospitals** onboarded. NHCX itself is government-run
infrastructure (the NHA/IRDAI role parallels e-Hospital/eSushrut in
the earlier section) — the companies actually doing the
eligibility-check and claim-submission work this app simulates are
**Third-Party Administrators (TPAs)**, which process claims on behalf
of insurers:

- **[Medi Assist](https://www.mediassist.in/about/)** — India's
  largest health-benefits administrator, listed on BSE/NSE, a 14,000+
  hospital network, and (as of July 2025) owner of **Paramount Health
  Services & Insurance TPA** after a full acquisition — so two of the
  names you'll see in this space are now the same company.
- **[Vidal Health](https://www.vidalhealthtpa.com/vidalhealthtpa)** —
  formed by a merger with Vipul MedCorp Insurance TPA, 29 branch
  offices, combined revenue around ₹200 crore.

**Germany (gematik TI):** the same eligibility/claim pattern here maps
onto gematik itself being the coordinating body (majority-owned by the
Federal Ministry of Health since 2019, the NHA-equivalent role) rather
than a vendor, while the actual **connector** software that hooks a
clinic or insurer into the TI network is built and sold by certified
vendors — **[CGM (CompuGroup Medical)](https://www.cgm.com/deu_de/loesungen/telematikinfrastruktur/produkte.html)**
is the most visible one, offering both an on-premises TI connector and
a hosted "CGM MANAGED TI" option, gematik-certified, in wide use since
2017.

In both countries the same shape recurs, and it's the shape this
repo's `_admit`/`_discharge` functions follow: a government body
defines the protocol and certifies participants, while separate
commercial entities (TPAs in India, connector vendors in Germany)
actually execute the eligibility checks and claim submissions.

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

## Real-world context: lab report digitization vendors

Background for anyone comparing this demo's `lab_ocr.py` to what
already exists in India — reference material, not something the app
implements or connects to.

- **[Ayu](https://ayuapp.com/)** (`ayuapp.com`, not to be confused
  with *Ayu Health*, the unrelated Bengaluru hospital-network operator
  of a similar name) is the closest real-world parallel to this repo's
  combined prescription + lab OCR: a consumer PHR app whose OCR reads
  10 Indian languages, extracts medication/dose/frequency from
  photographed handwritten prescriptions, pulls test
  parameters/reference ranges from lab reports, and parses discharge
  summaries — the same three document types this demo digitizes,
  aimed at families organizing records at home rather than a hospital
  system. Its own engineering stack couldn't be confirmed — and
  tellingly, a job-posting search for it surfaced a real stack (Java,
  Dropwizard, MySQL, Ruby, Scala) for *Ayu Health*, the unrelated
  hospital-network company this bullet already warns about. That's
  deliberately **not** reported as Ayu's stack here; it's a live
  demonstration of exactly the mix-up the disambiguation above exists
  to prevent.
- **[Eka.Care](https://www.eka.care/services/abdm-enabling-ecosystems)**
  (already the HIP+HIU example in the ABHA section above) also OCRs
  and structures lab reports as part of its PHR product.
- **Icanio Technologies** builds AI record-digitization platforms for
  Indian *hospitals* specifically — the enterprise/B2B side of the
  same problem, including OCR for handwritten records, rather than the
  consumer-app side Ayu and Eka.Care cover. Its job postings list a
  broad, generic full-stack/DevOps toolkit (Java/Python/JavaScript/C#,
  MySQL/PostgreSQL/MongoDB, Docker/Kubernetes) rather than one specific
  stack — consistent with being a general software-services company
  (web, mobile, AI, cloud) for which healthcare digitization is one
  case study among several, not a single-product healthcare company.
- **[Docsumo](https://www.docsumo.com/solutions/idp-for-healthcare)**
  (Mumbai, founded 2019) is a general Intelligent Document Processing
  platform with a healthcare/insurance vertical — extracting structured
  data from medical reports, prior-authorization requests, and claims
  at enterprise scale, closer to insurer/payer back-office automation
  than a hospital bedside tool. Job postings only thinly confirm a
  **Python**-centric stack, mostly visible through solutions-engineering
  roles (Python, REST APIs) rather than core-platform listings — not
  enough to describe their full engineering stack with confidence.

One number worth noting because it explains a real design choice this
repo shares: reported OCR accuracy on **standard NABL-format** lab
reports (NABL — India's National Accreditation Board for Testing and
Calibration Laboratories, which standardizes how accredited labs
format results) runs above 90% for structured extraction, meaningfully
higher than free-form handwriting. That's the same reason
`lab_ocr.py` only matches lines against a list of known analyte
names rather than trying to parse arbitrary text — recognizable,
standardized formatting is what makes automated extraction tractable
at all, in a real product or in this demo.

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

## Real-world context: discharge summary vendors

Background for anyone comparing this demo's `discharge_summary.py`
to what already exists — reference material, not something the app
implements or connects to.

**India:** **[Rivara Health](https://rivarahealth.com/)** is the
closest real-world match to this repo's whole loop, not just the
document — built specifically for **ICU** doctors in India, it
generates "medicolegal-grade" discharge summaries in under two
minutes from a doctor photographing handwritten bedside charts and
uploading lab reports, with AI extracting the clinical data
automatically. That's the same
photograph-→-OCR-→-structured-discharge-document pipeline this repo
implements, aimed at the same ICU setting. Unlike the other companies
in this README, no job posting or engineering-stack detail for Rivara
Health turned up in research for this section — small enough, or
early enough, to leave no public trace of it yet.

There's also a formal government standard this repo's own discharge
summary deliberately *doesn't* conform to: ABDM defines a
**[`DischargeSummaryRecord`](https://nrces.in/ndhm/fhir/r4/StructureDefinition-DischargeSummaryRecord.html)**
FHIR profile (maintained by NRCES, the National Resource Centre for
EHR Standards) as one of its standard Health Information Types,
alongside prescriptions and diagnostic reports — a hospital's HMIS is
expected to package a real discharge summary as a FHIR Bundle in that
shape before sharing it to a patient's ABHA/PHR app. A production
version of this feature would target that profile; this demo's JSON
+ printable-HTML pair is illustrative only, not interoperable with
real ABDM infrastructure.

**Elsewhere:** ambient AI clinical-documentation tools — **Nuance DAX
Copilot** (Microsoft, deep Epic/Cerner integration, 600+ health
organizations), **Abridge**, and **Suki AI** — record a clinician
encounter and draft structured notes, including discharge-adjacent
documentation, rather than digitizing photographed paper records the
way this repo and Rivara Health do. Worth noting because it's the
same caution this repo's mandatory disclaimers exist for, reported
independently in that space too: AI-generated notes can still miss
clinically relevant details or hallucinate medications, and require
physician review before signing — not a solved problem regardless of
which input modality (voice vs. photographed chart) generates the
draft.

Both Abridge and Suki AI's engineering job postings are public and
confirm real, mature stacks — Nuance DAX's aren't separately
identifiable, having been absorbed into Microsoft's much larger job
market. **Abridge**: **Node.js/TypeScript + React**, running on
**Google Cloud (GCP)**. **Suki AI**: broader — **Go, C++, Python**
backend, **React/TypeScript** web, native **Swift/Kotlin** mobile,
**gRPC/GraphQL** APIs, all on **GCP + Kubernetes**, plus a distinct
ML stack (**Vertex AI, PyTorch, JAX**) for the speech/NLP side — the
kind of breadth you'd expect from an ambient-voice product that needs
real-time mobile capture, backend transcription/NLP, and an EHR
integration layer all at once.

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

## Real-world context: ICU dashboard competitors

Background on the commercial products this whole repo is an analogue
of — the four named in the opening paragraph, checked here rather
than just asserted:

- **[vTitan (Jeevantra / IntelliICU)](https://www.vtitan.com/intelli-icu)** —
  Indian medical-device company (Chengalpattu, Tamil Nadu). IntelliICU
  is the same hardware-cum-software shape as this repo's design:
  connects to whatever mix of patient monitors, ventilators, and
  syringe pumps a hospital already has, unifying them into one
  dashboard; Jeevantra layers an AI chatbot for handover/medication/
  fluid decision support on top. Now has its own site
  ([intelliicu.com](https://intelliicu.com/)) distinct from vtitan.com.
  Their embedded-engineering job postings (Naukri) confirm the stack
  the hardware side runs on: **C/C++** on **bare-metal and RTOS**
  targeting **TI/ST microcontrollers**, over **I2C/SPI/UART/CAN** —
  a firmware shop, not a typical web stack, which tracks with owning
  the infusion-pump hardware rather than just the dashboard software.
- **[Etiometry](https://www.etiometry.com/)** — US, founded 2010, roots
  in pediatric ICU/cardiac care, now holds **11 FDA clearances** as a
  regulated clinical decision-support device (most recently for
  automating cardiogenic-shock staging from monitoring data). A
  published study at Children's Hospital of Alabama associated its use
  with a 30% reduction in mechanical ventilation duration and a 20%
  decrease in length of stay — real outcomes data behind a real
  regulatory approval, which is exactly the gap between this repo and
  an actual medical device (see [Status](#status)). Their software
  stack couldn't be confirmed — no public job listing surfaced it, and
  their careers page and LinkedIn job listings sit behind a login wall
  — so unlike the other three, nothing is asserted about it here.
- **[Dozee](https://www.dozeehealth.ai/for-hospitals)** — Indian
  contactless remote patient monitoring company: a under-mattress
  sensor turns any bed into a monitored one, no wires or cuffs. In
  named use at Apollo Hospitals, Wockhardt Hospitals, Breach Candy
  Hospital, and Vijaya Medical, with a `dozee.us` presence suggesting
  US expansion too. A Bangalore firmware-engineer listing confirms the
  sensor side runs on **C/C++** as well, for their proprietary
  ballistocardiography hardware — the same embedded-firmware pattern
  as vTitan, for the same reason: they own physical sensor hardware,
  not just software.
- **[AcuteCare.ai (CritIS)](https://www.acutecare.ai/en/about)** —
  originally a 2017 spin-off of the University of Crete (Greece),
  leading ICU/anaesthesia software provider at Greece's largest public
  university hospitals; **CritIS Tele-ICU** (the module named in this
  repo's opening line) is one module of their broader **CritIS
  Synergy+** platform. Partnered with Sievestone LTD in 2024 to expand
  globally beyond Greece. No job listing surfaced their stack, but
  their own [Technology Partners page](https://acutecare.ai/en/Technology-Partners)
  states it directly: **Java** backend, **Mirth Connect** for
  real-time HL7/FHIR interoperability, **MySQL** for storage, and the
  Java-based **CaptainCasa Enterprise Client Framework** for the UI —
  an enterprise-Java shape, unsurprising for software integrating with
  hospital IT rather than owning bedside hardware the way vTitan and
  Dozee do.

The common thread across all four: they're real, regulated (in
Etiometry's case, FDA-cleared) medical products deployed in named
hospitals, built by teams with device-integration and clinical
partnerships this repo has none of. That gap is deliberate — see
[Status](#status) for what this repo is and isn't. Their stacks also
split cleanly along that same line: the two companies that own
physical sensor/pump hardware (vTitan, Dozee) run embedded C/C++
firmware, while the one that's pure integration software (AcuteCare.ai)
runs an enterprise Java/HL7 stack — this repo, with no real hardware
and no real hospital integration, is neither, just a Python/FastAPI +
React demo over an open research dataset.

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

## Real-world context: infrastructure this demo doesn't have

Every "Real-world context" section above checked a real company's
actual stack. Laid side by side, they all have infrastructure-layer
components this repo doesn't — not code polish, whole categories of
component. Grepping this repo's own code confirms the gaps:

- **Persistence layer.** AcuteCare.ai and (per its own job postings)
  Ayu Health run MySQL, Innovaccer runs PostgreSQL, Icanio runs
  MongoDB. This repo has **no database** — `bed_prescriptions`,
  `bed_ocr_pending`, `health_record._records`, everything, lives in
  plain Python dicts in `main.py`/`health_record.py`. Restart the
  process and every patient, discharge summary, and approved lab
  result is gone.
- **Authentication / authorization.** Zero anywhere in `main.py` — no
  `Depends()`, no API keys, no sessions. Anyone who can reach port
  8710 can approve a fabricated prescription or discharge a patient.
  Real health software needs RBAC by regulatory default; this repo
  has no concept of *who* clicked Approve.
- **Containerization and a deploy story.** No Dockerfile, no
  docker-compose, no IaC. Suki AI, Eka.Care, Icanio, and CitiusTech
  job postings all list Docker/Kubernetes (Eka.Care adds Terraform).
  This repo's only "deploy" step is `uvicorn app.main:app` on
  localhost.
- **Horizontal scalability.** A direct consequence of the first two:
  state in module-level Python dicts means this app can only ever run
  as a single process, where a stateless-services-plus-shared-DB
  design can run N replicas behind a load balancer.
- **CI/CD and automated tests.** No `.github/` directory, and no test
  files belonging to this repo anywhere on disk (the only `test_*`
  matches found live inside third-party `.venv`/`node_modules`
  packages). Every company with public engineering job postings
  implies a pipeline running tests before merge; this repo has
  neither the tests nor the pipeline.
- **A real device-integration engine.** AcuteCare.ai's CritIS runs
  **Mirth Connect** for real HL7/FHIR traffic to bedside devices. This
  repo's "device integration" is VitalDB case-file playback —
  realistic-looking data, but no HL7v2/FHIR listener a real monitor
  could ever connect to. ([OpenICE](https://github.com/mdpnp/mdpnp),
  already in Reference Projects below, is the actual open-source
  example of what a real interface engine looks like.)
- **ML/AI inference infrastructure.** Suki AI lists a dedicated ML
  stack (Vertex AI, PyTorch, JAX) for real speech/NLP inference;
  Etiometry's entire product *is* an FDA-cleared ML risk-scoring
  model. This repo's "AI" (`prescription_ocr.py`, `lab_ocr.py`) is
  Tesseract OCR plus hand-written regex — no model training, no
  inference service, no ML framework in `requirements.txt` at all.
- **Native mobile clients.** Suki AI, Eka.Care, Dozee, vTitan, and Ayu
  all ship native iOS/Android apps — which matters specifically for
  bedside/ICU use, where a phone or tablet at the nurse's station is
  the real interface. This repo is React-web-only.
- **Observability.** Nothing beyond a bare `logging.info()` call — no
  structured logging, metrics, tracing, or error tracking.

The honest framing: this repo only builds the *application-layer
logic* — alert rules, the OCR review workflow, discharge-summary
aggregation, the insurance-claim state machine — and borrows VitalDB
for realistic data instead of building the infrastructure layer
underneath it. Every company checked in this README has that
infrastructure layer; this repo has none of it, by design.

## Status

Prototype/demo only. Not validated for clinical use, not a medical
device, and the alarm thresholds in `backend/app/alerts.py` are
illustrative defaults, not clinically reviewed limits. See the
infrastructure gaps immediately above for the concrete, specific
version of what "prototype" means here.
