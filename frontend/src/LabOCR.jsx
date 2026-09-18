import { useEffect, useRef, useState } from 'react'

const API_BASE = 'http://localhost:8710'

function CandidateRow({ bedId, candidate, onResolved }) {
  const [test, setTest] = useState(candidate.test)
  const [value, setValue] = useState(candidate.value ?? '')
  const [unit, setUnit] = useState(candidate.unit ?? '')
  const [range, setRange] = useState(candidate.reference_range ?? '')
  const [flag, setFlag] = useState(candidate.flag ?? '')
  const [busy, setBusy] = useState(false)

  const approve = async () => {
    setBusy(true)
    await fetch(`${API_BASE}/api/beds/${bedId}/labs/pending/${candidate.id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        test,
        value: value || null,
        unit: unit || null,
        reference_range: range || null,
        flag: flag || null,
      }),
    })
    onResolved()
  }

  const reject = async () => {
    setBusy(true)
    await fetch(`${API_BASE}/api/beds/${bedId}/labs/pending/${candidate.id}/reject`, { method: 'POST' })
    onResolved()
  }

  return (
    <div className="ocr-candidate">
      <div className="ocr-raw-line">OCR read: &ldquo;{candidate.raw_line}&rdquo;</div>
      <div className="ocr-fields ocr-fields-lab">
        <input value={test} onChange={(e) => setTest(e.target.value)} placeholder="Test" />
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Value" />
        <input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="Unit" />
        <input value={range} onChange={(e) => setRange(e.target.value)} placeholder="Reference range" />
        <input value={flag} onChange={(e) => setFlag(e.target.value)} placeholder="Flag" />
      </div>
      <div className="ocr-actions">
        <button className="ocr-approve" disabled={busy} onClick={approve}>Approve</button>
        <button className="ocr-reject" disabled={busy} onClick={reject}>Reject</button>
      </div>
    </div>
  )
}

export default function LabOCR({ bedId, onApproved }) {
  const [pending, setPending] = useState([])
  const [rawText, setRawText] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const loadPending = () => {
    fetch(`${API_BASE}/api/beds/${bedId}/labs/pending`)
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
      const res = await fetch(`${API_BASE}/api/beds/${bedId}/labs/ocr`, { method: 'POST', body: form })
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
        <h3>Lab report OCR digitization</h3>
        <p className="source-note">
          Upload a photo of a lab report. Local OCR (Tesseract) extracts candidate test/value/range lines &mdash;
          nothing is recorded as a result until you review and approve it below. OCR frequently loses decimal
          points and garbles units, so check every value against the report before approving.
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
