import { useEffect, useRef, useState } from 'react'

const API_BASE = 'http://localhost:8710'

function CandidateRow({ bedId, candidate, onResolved }) {
  const [drug, setDrug] = useState(candidate.drug)
  const [dose, setDose] = useState(candidate.dose ?? '')
  const [route, setRoute] = useState(candidate.route ?? '')
  const [freq, setFreq] = useState(candidate.frequency_sim_sec ?? '')
  const [busy, setBusy] = useState(false)

  const approve = async () => {
    setBusy(true)
    await fetch(`${API_BASE}/api/beds/${bedId}/prescriptions/pending/${candidate.id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        drug,
        dose: dose || null,
        route: route || null,
        frequency_sim_sec: freq === '' ? null : Number(freq),
      }),
    })
    onResolved()
  }

  const reject = async () => {
    setBusy(true)
    await fetch(`${API_BASE}/api/beds/${bedId}/prescriptions/pending/${candidate.id}/reject`, { method: 'POST' })
    onResolved()
  }

  return (
    <div className="ocr-candidate">
      <div className="ocr-raw-line">OCR read: &ldquo;{candidate.raw_line}&rdquo;</div>
      <div className="ocr-fields">
        <input value={drug} onChange={(e) => setDrug(e.target.value)} placeholder="Drug" />
        <input value={dose} onChange={(e) => setDose(e.target.value)} placeholder="Dose" />
        <input value={route} onChange={(e) => setRoute(e.target.value)} placeholder="Route" />
        <input
          value={freq}
          onChange={(e) => setFreq(e.target.value)}
          placeholder="Cadence (sim-sec, blank = as-needed)"
        />
      </div>
      <div className="ocr-actions">
        <button className="ocr-approve" disabled={busy} onClick={approve}>Approve</button>
        <button className="ocr-reject" disabled={busy} onClick={reject}>Reject</button>
      </div>
    </div>
  )
}

export default function PrescriptionOCR({ bedId, onApproved }) {
  const [pending, setPending] = useState([])
  const [rawText, setRawText] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const loadPending = () => {
    fetch(`${API_BASE}/api/beds/${bedId}/prescriptions/pending`)
      .then((r) => r.json())
      .then((d) => setPending(d.candidates))
  }

  useEffect(() => {
    loadPending()
  }, [bedId])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_BASE}/api/beds/${bedId}/prescriptions/ocr`, { method: 'POST', body: form })
      if (!res.ok) throw new Error((await res.json()).detail ?? 'OCR failed')
      const data = await res.json()
      setRawText(data.raw_text)
      loadPending()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleResolved = () => {
    loadPending()
    onApproved?.()
  }

  return (
    <div className="rx-panel">
      <div className="rx-header">
        <h3>Prescription OCR digitization</h3>
        <p className="source-note">
          Upload a photo of a written prescription. Local OCR (Tesseract) extracts candidate drug/dose/route/cadence
          lines &mdash; nothing becomes an active order until you review and approve it below.
        </p>
      </div>

      <input ref={fileInputRef} type="file" accept="image/*" onChange={handleUpload} disabled={uploading} />
      {uploading && <p className="source-note">Running OCR...</p>}
      {error && <p className="ocr-error">{error}</p>}

      {rawText && (
        <details className="ocr-raw-text">
          <summary>Raw OCR text</summary>
          <pre>{rawText}</pre>
        </details>
      )}

      {pending.length > 0 && (
        <div className="ocr-candidates">
          {pending.map((c) => (
            <CandidateRow key={c.id} bedId={bedId} candidate={c} onResolved={handleResolved} />
          ))}
        </div>
      )}
    </div>
  )
}
