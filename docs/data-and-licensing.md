# Data sources, licensing and swapping in real ICU data

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

