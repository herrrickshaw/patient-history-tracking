"""Generates a discharge summary document at the end of each encounter,
compiled from the same ABHA-linked data this demo already tracks:
identity, the vitals range observed, alarms raised, medications given,
and the insurance-connect claim outcome.

Illustrative demo document only. It is not a real clinical discharge
summary, was not reviewed by any clinician, and must not be used for
actual patient care.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

DISCLAIMER = (
    "Auto-generated demo discharge summary, compiled from simulated vitals, "
    "alarms, medications, reviewer-approved lab results, and insurance-connect "
    "data for this encounter. Not a real clinical document, not reviewed by "
    "any clinician, and not suitable for actual patient care."
)

VITAL_LABELS = {"HR": "Heart rate (bpm)", "SPO2": "SpO2 (%)", "NIBP_SBP": "NIBP systolic (mmHg)",
                 "NIBP_DBP": "NIBP diastolic (mmHg)", "RR": "Resp. rate (/min)", "TEMP": "Temperature (°C)"}

_summaries: dict[str, list[dict]] = {}


def build(
    identity: dict,
    admitted_sim_t: int,
    discharged_sim_t: int,
    vitals_range: dict,
    alert_events: list[dict],
    medication_events: list[dict],
    claim: dict,
    lab_events: list[dict] | None = None,
) -> dict:
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "abha_id": identity["abha_id"],
        "name": identity["name"],
        "age": identity.get("age"),
        "sex": identity.get("sex"),
        "department": identity.get("department"),
        "procedure": identity.get("procedure"),
        "diagnosis": identity.get("diagnosis"),
        "admitted_sim_t": admitted_sim_t,
        "discharged_sim_t": discharged_sim_t,
        "duration_sim_sec": discharged_sim_t - admitted_sim_t,
        "vitals_range": vitals_range,
        "alerts": alert_events,
        "medications": medication_events,
        "lab_results": lab_events or [],
        "insurance_claim": claim,
        "disclaimer": DISCLAIMER,
    }
    _summaries.setdefault(identity["abha_id"], []).append(summary)
    return summary


def latest(abha_id: str) -> dict | None:
    items = _summaries.get(abha_id)
    return items[-1] if items else None


def _esc(value) -> str:
    return html.escape(str(value)) if value is not None else "—"


def render_html(summary: dict) -> str:
    vitals_rows = "".join(
        f"<tr><td>{_esc(VITAL_LABELS.get(k, k))}</td><td>{_esc(v.get('min'))}</td>"
        f"<td>{_esc(v.get('max'))}</td><td>{_esc(v.get('last'))}</td></tr>"
        for k, v in summary["vitals_range"].items()
    )
    alert_rows = "".join(
        f"<li>t={_esc(e['sim_t'])}s — {_esc(e['payload'].get('message', e['payload'].get('vital')))}</li>"
        for e in summary["alerts"]
    ) or "<li>None recorded</li>"
    med_rows = "".join(
        f"<li>t={_esc(e['sim_t'])}s — {_esc(e['payload']['drug'])} {_esc(e['payload']['dose'])} "
        f"({_esc(e['payload']['route'])})</li>"
        for e in summary["medications"]
    ) or "<li>None recorded</li>"
    lab_rows = "".join(
        f"<tr><td>{_esc(e['payload']['test'])}</td><td>{_esc(e['payload']['value'])} {_esc(e['payload']['unit'] or '')}</td>"
        f"<td>{_esc(e['payload']['reference_range'])}</td><td>{_esc(e['payload']['flag'])}</td></tr>"
        for e in summary["lab_results"]
    )
    claim = summary["insurance_claim"] or {}

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Discharge Summary (Demo) — {_esc(summary['name'])}</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background:#0b0f14; color:#e6edf3; margin:0; padding:24px; }}
  .doc {{ max-width: 760px; margin: 0 auto; }}
  .banner {{ background:#ef4444; color:#1a0000; font-weight:700; text-align:center; padding:10px; border-radius:8px; margin-bottom:20px; }}
  h1 {{ font-size: 20px; margin-bottom: 2px; }}
  h2 {{ font-size: 14px; color:#7d8b98; text-transform:uppercase; letter-spacing:.04em; margin: 22px 0 8px; }}
  .meta {{ color:#7d8b98; font-size: 13px; }}
  table {{ width:100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align:left; padding: 5px 8px; border-bottom: 1px solid #1f2933; }}
  ul {{ margin: 4px 0; padding-left: 20px; font-size: 13px; }}
  .disclaimer {{ margin-top: 26px; font-size: 11.5px; color:#7d8b98; border-top:1px solid #1f2933; padding-top:10px; }}
  @media print {{ body {{ background:#fff; color:#000; }} .banner {{ -webkit-print-color-adjust: exact; }} }}
</style></head>
<body>
<div class="doc">
  <div class="banner">SYNTHETIC DEMO DOCUMENT &mdash; NOT A REAL DISCHARGE SUMMARY &mdash; NOT FOR CLINICAL USE</div>
  <h1>Discharge Summary (Demo)</h1>
  <div class="meta">Document generated {_esc(summary['generated_at'])}</div>

  <h2>Patient</h2>
  <div>{_esc(summary['name'])} &middot; {_esc(summary['age'])}y &middot; {_esc(summary['sex'])}</div>
  <div class="meta">ABHA-style ID (demo): {_esc(summary['abha_id'])}</div>

  <h2>Encounter</h2>
  <div>{_esc(summary['department'])} &mdash; {_esc(summary['procedure'])}</div>
  <div class="meta">Diagnosis: {_esc(summary['diagnosis'])}</div>
  <div class="meta">Simulated duration: {_esc(summary['duration_sim_sec'])} sim-seconds
    (sim-time t={_esc(summary['admitted_sim_t'])} → t={_esc(summary['discharged_sim_t'])})</div>

  <h2>Vitals observed (range)</h2>
  <table><thead><tr><th>Vital</th><th>Min</th><th>Max</th><th>Last</th></tr></thead>
  <tbody>{vitals_rows}</tbody></table>

  <h2>Alerts during encounter</h2>
  <ul>{alert_rows}</ul>

  <h2>Medications administered</h2>
  <ul>{med_rows}</ul>

  <h2>Lab results (OCR-digitized, reviewer-approved)</h2>
  {"<table><thead><tr><th>Test</th><th>Value</th><th>Reference range</th><th>Flag</th></tr></thead>"
   f"<tbody>{lab_rows}</tbody></table>" if lab_rows else "<div>None recorded</div>"}

  <h2>Insurance (simulated)</h2>
  <div>{_esc(claim.get('insurer'))} &middot; claim {_esc(claim.get('claim_id'))} &middot;
    {_esc(claim.get('amount_estimate'))} units &middot; {_esc(claim.get('status'))}</div>

  <div class="disclaimer">{_esc(summary['disclaimer'])}</div>
</div>
</body></html>"""
