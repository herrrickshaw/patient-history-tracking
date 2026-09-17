import { useEffect, useRef } from 'react'

// Real-time scrolling monitor strip for one waveform channel, drawn on
// canvas since a single trace can carry thousands of points per second.
export default function WaveformCanvas({ label, color, bufferRef, height = 90 }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    let raf

    function draw() {
      const { width, height: h } = canvas
      ctx.clearRect(0, 0, width, h)
      const buf = bufferRef.current
      const points = buf.filter((v) => v !== null && v !== undefined)
      if (points.length > 1) {
        const min = Math.min(...points)
        const max = Math.max(...points)
        const range = max - min || 1
        ctx.beginPath()
        ctx.strokeStyle = color
        ctx.lineWidth = 1.5
        buf.forEach((v, i) => {
          if (v === null || v === undefined) return
          const x = (i / (buf.length - 1)) * width
          const y = h - ((v - min) / range) * (h - 8) - 4
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        })
        ctx.stroke()
      }
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [bufferRef, color])

  return (
    <div className="waveform-block">
      <div className="waveform-label">{label}</div>
      <canvas ref={canvasRef} width={800} height={height} className="waveform-canvas" />
    </div>
  )
}
