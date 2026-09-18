export default function LabResults({ record }) {
  if (!record) return null
  return (
    <div className="rx-panel">
      <div className="rx-header">
        <h3>Lab results</h3>
        <p className="source-note">{record.disclaimer}</p>
      </div>
      <table className="rx-table">
        <thead>
          <tr>
            <th>Test</th>
            <th>Value</th>
            <th>Reference range</th>
            <th>Flag</th>
          </tr>
        </thead>
        <tbody>
          {record.results.map((r, i) => (
            <tr key={i}>
              <td>{r.test}</td>
              <td>{r.value} {r.unit ?? ''}</td>
              <td>{r.reference_range ?? '--'}</td>
              <td className={`rx-status rx-flag-${r.flag ?? 'unknown'}`}>{r.flag ?? '--'}</td>
            </tr>
          ))}
          {record.results.length === 0 && (
            <tr>
              <td colSpan={4} className="timeline-empty">No approved lab results yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
