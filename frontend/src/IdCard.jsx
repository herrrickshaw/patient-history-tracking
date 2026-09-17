export default function IdCard({ identity }) {
  if (!identity) return null
  return (
    <div className="id-card">
      <div className="id-card-banner">DEMO ID &mdash; not a real ABHA record</div>
      <div className="id-card-body">
        <div className="id-card-qr" title="Placeholder only, not a scannable code" />
        <div className="id-card-fields">
          <div className="id-card-name">{identity.name}</div>
          <div className="id-card-abha">ABHA-style ID: {identity.abha_id}</div>
          <div className="id-card-row">
            <span>{identity.age ? `${identity.age}y` : '--'}</span>
            <span>{identity.sex ?? '--'}</span>
            <span>ASA {identity.asa_class ?? '--'}</span>
          </div>
          <div className="id-card-row muted">{identity.department}</div>
          <div className="id-card-row muted">{identity.procedure}</div>
          <div className="id-card-row muted">{identity.diagnosis}</div>
        </div>
      </div>
      <div className="id-card-disclaimer">{identity.disclaimer}</div>
    </div>
  )
}
