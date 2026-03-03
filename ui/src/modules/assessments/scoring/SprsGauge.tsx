interface Props {
  score: number | null
}

const SPRS_MIN = -203
const SPRS_MAX = 110
const SPRS_RANGE = SPRS_MAX - SPRS_MIN // 313

function getColor(score: number): string {
  if (score < -50) return '#ef4444'   // red-500
  if (score <= 0) return '#f97316'    // orange-500
  if (score <= 54) return '#eab308'   // yellow-500
  return '#22c55e'                     // green-500
}

function getTrackColor(score: number): string {
  if (score < -50) return '#fecaca'   // red-200
  if (score <= 0) return '#fed7aa'    // orange-200
  if (score <= 54) return '#fef08a'   // yellow-200
  return '#bbf7d0'                     // green-200
}

export default function SprsGauge({ score }: Props) {
  // SVG semi-circle gauge
  const cx = 60
  const cy = 55
  const r = 44
  const startAngle = Math.PI       // 180 degrees (left)
  const endAngle = 0               // 0 degrees (right)
  const strokeWidth = 8

  // Normalized position on the arc (0 = left/min, 1 = right/max)
  const normalized = score != null ? Math.max(0, Math.min(1, (score - SPRS_MIN) / SPRS_RANGE)) : 0

  // SVG arc path helper
  function arcPath(startFrac: number, endFrac: number): string {
    const a1 = Math.PI - startFrac * Math.PI
    const a2 = Math.PI - endFrac * Math.PI
    const x1 = cx + r * Math.cos(a1)
    const y1 = cy - r * Math.sin(a1)
    const x2 = cx + r * Math.cos(a2)
    const y2 = cy - r * Math.sin(a2)
    const largeArc = endFrac - startFrac > 0.5 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`
  }

  const color = score != null ? getColor(score) : '#d1d5db'
  const trackColor = score != null ? getTrackColor(score) : '#e5e7eb'

  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="70" viewBox="0 0 120 70" role="img" aria-label={`SPRS Score: ${score ?? 'not available'}`}>
        {/* Background track */}
        <path
          d={arcPath(0, 1)}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        {score != null && normalized > 0.005 && (
          <path
            d={arcPath(0, normalized)}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
        )}
        {/* Score text */}
        <text x={cx} y={cy - 4} textAnchor="middle" className="text-base font-bold" fill="currentColor" fontSize="18">
          {score != null ? String(score) : '—'}
        </text>
        {/* Range labels */}
        <text x={cx - r} y={cy + 12} textAnchor="middle" className="text-xs" fill="#9ca3af" fontSize="8">
          {SPRS_MIN}
        </text>
        <text x={cx + r} y={cy + 12} textAnchor="middle" className="text-xs" fill="#9ca3af" fontSize="8">
          {SPRS_MAX}
        </text>
      </svg>
      <span className="text-xs text-base-content/60 -mt-1">SPRS Score</span>
    </div>
  )
}
