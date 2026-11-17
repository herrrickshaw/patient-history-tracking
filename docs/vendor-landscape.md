# Real-world context and vendor landscape

Background research moved verbatim from the previous README. Reference material only: the app does not implement or connect to any of these systems. Figures are as of the date of the original research and were not re-verified in this refactor.

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

> Update (2026-11 refactor): the repo now has a pytest suite (`backend/tests/`) and a GitHub Actions workflow (`.github/workflows/ci.yml`), so the "CI/tests" gap named below is partly closed. Auth, containerization, a device-integration engine, ML inference, mobile clients and observability are still absent.

Every "Real-world context" section above checked a real company's
actual stack. Laid side by side, they all have infrastructure-layer
components this repo doesn't — not code polish, whole categories of
component. Grepping this repo's own code confirms the gaps below —
except the first one, which has since been closed (see
[Persistence layer](#persistence-layer) near the top of this README):

- ~~**Persistence layer.**~~ **Closed.** AcuteCare.ai and (per its own
  job postings) Ayu Health run MySQL, Innovaccer runs PostgreSQL,
  Icanio runs MongoDB — all a step up from what this repo now has,
  SQLite behind a single process, but the state itself (prescriptions,
  the health-record timeline, discharge summaries, insurance records)
  now genuinely survives a restart instead of living in plain Python
  dicts that reset to nothing. Still a gap relative to those
  companies: no horizontal scalability (a direct consequence of
  "single SQLite file, single process"), and the next bullet below —
  auth — is unrelated to persistence and remains fully open.
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
- **Horizontal scalability.** Persistence closed the "state resets on
  restart" gap, but not this one: a single local SQLite file still
  means this app can only ever run as one process, where a real
  stateless-services-plus-shared-DB design (Postgres/MySQL reachable
  over the network, like the companies above) can run N replicas
  behind a load balancer.
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

The honest framing: this repo mostly builds the *application-layer
logic* — alert rules, the OCR review workflow, discharge-summary
aggregation, the insurance-claim state machine — and borrows VitalDB
for realistic data instead of building the infrastructure layer
underneath it. Persistence is the one piece of that infrastructure
layer this repo now has, built the way this codebase builds
everything (plain, minimal, matching the existing style) rather than
matching any specific company's choice of Postgres/MySQL/MongoDB. The
rest of the list above — auth, containerization, CI/tests, a real
device-integration engine, ML inference, mobile clients,
observability — every company checked in this README has; this repo
still has none of it, by design, until asked for.


