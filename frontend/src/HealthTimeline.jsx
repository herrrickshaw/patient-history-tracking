const TYPE_LABELS = {
  admission: 'Admitted',
  alert_raised: 'Alert raised',
  alert_resolved: 'Alert resolved',
  vitals_snapshot: 'Vitals snapshot',
}

function describe(event) {
  switch (event.type) {
    case 'admission':
      return `${event.payload.department} — ${event.payload.procedure}`
    case 'alert_raised':
    case 'alert_resolved':
      return event.payload.message ?? event.payload.vital
    case 'vitals_snapshot':
      return Object.entries(event.payload)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => `${k} ${v}`)
        .join(' · ')
    default:
      return ''
  }
}

export default function HealthTimeline({ record }) {
  if (!record) return null
  return (
    <div className="timeline-panel">
      <div className="timeline-header">
        <h3>Health information history</h3>
        <p className="source-note">{record.disclaimer}</p>
      </div>
      <ul className="timeline-list">
        {record.timeline.map((event, i) => (
          <li key={i} className={`timeline-event timeline-${event.type}`}>
            <span className="timeline-type">{TYPE_LABELS[event.type] ?? event.type}</span>
            <span className="timeline-detail">{describe(event)}</span>
            <span className="timeline-source">{event.source}</span>
          </li>
        ))}
        {record.timeline.length === 0 && <li className="timeline-empty">No events recorded yet.</li>}
      </ul>
    </div>
  )
}
