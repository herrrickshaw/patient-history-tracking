const VITAL_LABELS = {
  HR: 'Heart rate (bpm)',
  SPO2: 'SpO2 (%)',
  NIBP_SBP: 'NIBP systolic (mmHg)',
  NIBP_DBP: 'NIBP diastolic (mmHg)',
  RR: 'Resp. rate (/min)',
  TEMP: 'Temperature (°C)',
}

const API_BASE = 'http://localhost:8710'

export default function DischargeSummaryPanel({ bedId, summary }) {
  if (!summary?.available) {
    return (
      <div className="rx-panel">
        <div className="rx-header">
          <h3>Discharge summary</h3>
          <p className="source-note">
            Generated automatically when this encounter is discharged (naturally, or every ~10s on the
            fast-cycle demo bed).
          </p>
        </div>
        <p className="timeline-empty">No discharge summary yet for this bed.</p>
      </div>
    )
  }

  return (
    <div className="rx-panel">
      <div className="rx-header dsum-header">
        <div>
          <h3>Discharge summary</h3>
          <p className="source-note">
            Last encounter: t={summary.admitted_sim_t}s &rarr; t={summary.discharged_sim_t}s
            ({summary.duration_sim_sec}s simulated)
          </p>
        </div>
        <a
          className="dsum-open-link"
          href={`${API_BASE}/api/beds/${bedId}/discharge-summary.html`}
          target="_blank"
          rel="noreferrer"
        >
          Open printable document &rarr;
        </a>
      </div>

      <table className="rx-table">
        <thead>
          <tr><th>Vital</th><th>Min</th><th>Max</th><th>Last</th></tr>
        </thead>
        <tbody>
          {Object.entries(summary.vitals_range).map(([key, v]) => (
            <tr key={key}>
              <td>{VITAL_LABELS[key] ?? key}</td>
              <td>{v.min}</td>
              <td>{v.max}</td>
              <td>{v.last}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {summary.lab_results?.length > 0 && (
        <table className="rx-table">
          <thead>
            <tr><th>Test</th><th>Value</th><th>Reference range</th><th>Flag</th></tr>
          </thead>
          <tbody>
            {summary.lab_results.map((e, i) => (
              <tr key={i}>
                <td>{e.payload.test}</td>
                <td>{e.payload.value} {e.payload.unit ?? ''}</td>
                <td>{e.payload.reference_range ?? '--'}</td>
                <td className={`rx-flag-${e.payload.flag ?? 'unknown'}`}>{e.payload.flag ?? '--'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p className="source-note">{summary.disclaimer}</p>
    </div>
  )
}
