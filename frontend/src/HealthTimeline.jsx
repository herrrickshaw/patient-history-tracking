const TYPE_LABELS = {
  admission: 'Admitted',
  discharge: 'Discharged',
  alert_raised: 'Alert raised',
  alert_resolved: 'Alert resolved',
  vitals_snapshot: 'Vitals snapshot',
  insurance_eligibility_checked: 'Eligibility checked',
  insurance_claim_submitted: 'Claim submitted',
  prescription_ordered: 'Prescriptions ordered',
  prescription_discontinued: 'Prescriptions discontinued',
  medication_administered: 'Medication given',
  discharge_summary_ready: 'Discharge summary ready',
  prescription_ocr_digitized: 'Prescription photo digitized',
  prescription_ocr_approved: 'OCR order approved',
  prescription_ocr_rejected: 'OCR order rejected',
  lab_report_digitized: 'Lab report photo digitized',
  lab_result_approved: 'Lab result approved',
  lab_result_rejected: 'Lab result rejected',
}

function describe(event) {
  switch (event.type) {
    case 'admission':
      return `${event.payload.department} — ${event.payload.procedure}`
    case 'discharge':
      return 'Encounter closed'
    case 'alert_raised':
    case 'alert_resolved':
      return event.payload.message ?? event.payload.vital
    case 'vitals_snapshot':
      return Object.entries(event.payload)
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([k, v]) => `${k} ${v}`)
        .join(' · ')
    case 'insurance_eligibility_checked':
      return `${event.payload.insurer} — ${event.payload.status} (${event.payload.authorization_ref})`
    case 'insurance_claim_submitted':
      return `${event.payload.claim_id} — ${event.payload.amount_estimate} units — ${event.payload.status}`
    case 'prescription_ordered':
      return event.payload.drugs.join(', ')
    case 'prescription_discontinued':
      return 'All active orders discontinued'
    case 'medication_administered':
      return `${event.payload.drug} ${event.payload.dose} (${event.payload.route})`
    case 'discharge_summary_ready':
      return 'See discharge summary below'
    case 'prescription_ocr_digitized':
      return `${event.payload.candidate_count} candidate line(s) awaiting review`
    case 'prescription_ocr_approved':
      return `${event.payload.drug} ${event.payload.dose} (from "${event.payload.raw_line}")`
    case 'prescription_ocr_rejected':
      return `Discarded: "${event.payload.raw_line}"`
    case 'lab_report_digitized':
      return `${event.payload.candidate_count} candidate line(s) awaiting review`
    case 'lab_result_approved':
      return `${event.payload.test} ${event.payload.value} ${event.payload.unit ?? ''} (${event.payload.flag ?? 'unflagged'})`
    case 'lab_result_rejected':
      return `Discarded: "${event.payload.raw_line}"`
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
