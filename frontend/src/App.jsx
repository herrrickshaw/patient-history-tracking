import { useEffect, useRef, useState } from 'react'
import PatientTile from './PatientTile.jsx'
import './App.css'

const WS_URL = 'ws://localhost:8710/ws/vitals'
const HISTORY_LEN = 40

export default function App() {
  const [bedsById, setBedsById] = useState({})
  const [connected, setConnected] = useState(false)
  const historyRef = useRef({})

  useEffect(() => {
    let socket
    let retryTimer

    function connect() {
      socket = new WebSocket(WS_URL)
      socket.onopen = () => setConnected(true)
      socket.onclose = () => {
        setConnected(false)
        retryTimer = setTimeout(connect, 2000)
      }
      socket.onerror = () => socket.close()
      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type !== 'tick') return
        const next = {}
        for (const bed of msg.beds) {
          next[bed.bed_id] = bed
          const hist = historyRef.current[bed.bed_id] ?? []
          historyRef.current[bed.bed_id] = [...hist, bed.vitals].slice(-HISTORY_LEN)
        }
        setBedsById(next)
      }
    }

    connect()
    return () => {
      clearTimeout(retryTimer)
      socket?.close()
    }
  }, [])

  const beds = Object.values(bedsById).sort((a, b) => a.bed_id.localeCompare(b.bed_id))
  const activeAlerts = beds.reduce((n, b) => n + b.alerts.length, 0)

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>ICU Dashboard Analogue</h1>
        <div className="status-line">
          <span className={`conn-dot ${connected ? 'conn-up' : 'conn-down'}`} />
          {connected ? `${beds.length} beds live` : 'connecting to backend...'}
          {activeAlerts > 0 && <span className="alert-count">{activeAlerts} active alert{activeAlerts === 1 ? '' : 's'}</span>}
        </div>
        <p className="source-note">
          Vitals replayed from real, de-identified cases in the open{' '}
          <a href="https://vitaldb.net" target="_blank" rel="noreferrer">VitalDB</a> dataset.
        </p>
      </header>
      <main className="bed-grid">
        {beds.map((bed) => (
          <PatientTile key={bed.bed_id} bed={bed} history={historyRef.current[bed.bed_id] ?? []} />
        ))}
      </main>
    </div>
  )
}
