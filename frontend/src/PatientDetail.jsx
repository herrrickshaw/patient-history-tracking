import { useEffect, useRef, useState } from 'react'
import IdCard from './IdCard.jsx'
import HealthTimeline from './HealthTimeline.jsx'
import WaveformCanvas from './WaveformCanvas.jsx'

const API_BASE = 'http://localhost:8710'
const WS_BASE = 'ws://localhost:8710'
const WAVEFORM_BUFFER_LEN = 1200 // ~12 sim-seconds at 100Hz

export default function PatientDetail({ bedId, onClose }) {
  const [identity, setIdentity] = useState(null)
  const [record, setRecord] = useState(null)
  const ecgBuffer = useRef(new Array(WAVEFORM_BUFFER_LEN).fill(null))
  const plethBuffer = useRef(new Array(WAVEFORM_BUFFER_LEN).fill(null))

  useEffect(() => {
    fetch(`${API_BASE}/api/beds/${bedId}/identity`).then((r) => r.json()).then(setIdentity)
  }, [bedId])

  useEffect(() => {
    const load = () => fetch(`${API_BASE}/api/beds/${bedId}/record`).then((r) => r.json()).then(setRecord)
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [bedId])

  useEffect(() => {
    ecgBuffer.current = new Array(WAVEFORM_BUFFER_LEN).fill(null)
    plethBuffer.current = new Array(WAVEFORM_BUFFER_LEN).fill(null)

    let socket
    let retryTimer
    function connect() {
      socket = new WebSocket(`${WS_BASE}/ws/waveform/${bedId}`)
      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type !== 'wave') return
        ecgBuffer.current = [...ecgBuffer.current, ...msg.ECG].slice(-WAVEFORM_BUFFER_LEN)
        plethBuffer.current = [...plethBuffer.current, ...msg.PLETH].slice(-WAVEFORM_BUFFER_LEN)
      }
      socket.onclose = () => {
        retryTimer = setTimeout(connect, 2000)
      }
      socket.onerror = () => socket.close()
    }
    connect()
    return () => {
      clearTimeout(retryTimer)
      socket?.close()
    }
  }, [bedId])

  return (
    <div className="detail-view">
      <button className="back-button" onClick={onClose}>&larr; Back to bed grid</button>
      <h2>{bedId} &mdash; patient detail</h2>

      <div className="detail-columns">
        <div className="detail-col">
          <IdCard identity={identity} />
        </div>
        <div className="detail-col detail-col-wide">
          <div className="waveform-panel">
            <WaveformCanvas label="ECG II" color="#3ecf8e" bufferRef={ecgBuffer} />
            <WaveformCanvas label="Pleth (SpO2)" color="#4ea1ff" bufferRef={plethBuffer} />
          </div>
        </div>
      </div>

      <HealthTimeline record={record} />
    </div>
  )
}
