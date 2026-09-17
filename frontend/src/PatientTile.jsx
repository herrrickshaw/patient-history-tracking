const VITAL_LABELS = {
  HR: 'HR',
  SPO2: 'SpO2',
  NIBP_SBP: 'NIBP',
  RR: 'RR',
  TEMP: 'Temp',
}

const VITAL_UNITS = {
  HR: 'bpm',
  SPO2: '%',
  NIBP_SBP: 'mmHg',
  RR: '/min',
  TEMP: '°C',
}

function levelForVital(vital, alerts) {
  const hit = alerts.find((a) => a.vital === vital)
  return hit ? hit.level : 'ok'
}

function Sparkline({ values, level }) {
  const nums = values.filter((v) => v !== null && v !== undefined)
  if (nums.length < 2) return <svg className="spark" viewBox="0 0 100 24" />
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const range = max - min || 1
  const points = values
    .map((v, i) => {
      if (v === null || v === undefined) return null
      const x = (i / (values.length - 1)) * 100
      const y = 24 - ((v - min) / range) * 22 - 1
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .filter(Boolean)
    .join(' ')
  return (
    <svg className={`spark spark-${level}`} viewBox="0 0 100 24" preserveAspectRatio="none">
      <polyline points={points} fill="none" strokeWidth="2" />
    </svg>
  )
}

export default function PatientTile({ bed, history }) {
  const { bed_id, vitals, alerts, case_id } = bed
  const worst = alerts.some((a) => a.level === 'critical')
    ? 'critical'
    : alerts.some((a) => a.level === 'warning')
      ? 'warning'
      : 'ok'

  return (
    <div className={`tile tile-${worst}`}>
      <div className="tile-header">
        <span className="bed-id">{bed_id}</span>
        <span className="case-id">VitalDB #{case_id}</span>
      </div>
      <div className="vitals-grid">
        {Object.keys(VITAL_LABELS).map((key) => {
          const level = levelForVital(key, alerts)
          const value = vitals[key]
          return (
            <div key={key} className={`vital vital-${level}`}>
              <div className="vital-label">{VITAL_LABELS[key]}</div>
              <div className="vital-value">
                {value ?? '--'}
                <span className="vital-unit">{VITAL_UNITS[key]}</span>
              </div>
              <Sparkline values={history.map((h) => h[key])} level={level} />
            </div>
          )
        })}
      </div>
      {alerts.length > 0 && (
        <ul className="alert-list">
          {alerts.map((a) => (
            <li key={a.vital} className={`alert alert-${a.level}`}>
              {a.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
