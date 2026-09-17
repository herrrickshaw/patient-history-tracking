const STATUS_LABEL = {
  active: 'Active',
  discontinued: 'Discontinued',
}

export default function PrescriptionTracker({ record }) {
  if (!record) return null
  return (
    <div className="rx-panel">
      <div className="rx-header">
        <h3>Prescription tracker</h3>
        <p className="source-note">{record.disclaimer}</p>
      </div>
      <table className="rx-table">
        <thead>
          <tr>
            <th>Drug</th>
            <th>Dose</th>
            <th>Route</th>
            <th>Cadence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {record.orders.map((o, i) => (
            <tr key={i} className={`rx-row-${o.status}`}>
              <td>{o.drug}</td>
              <td>{o.dose}</td>
              <td>{o.route}</td>
              <td>{o.frequency_sim_sec ? `every ${o.frequency_sim_sec}s (demo)` : 'continuous'}</td>
              <td className={`rx-status rx-status-${o.status}`}>{STATUS_LABEL[o.status] ?? o.status}</td>
            </tr>
          ))}
          {record.orders.length === 0 && (
            <tr>
              <td colSpan={5} className="timeline-empty">No orders for this encounter.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
