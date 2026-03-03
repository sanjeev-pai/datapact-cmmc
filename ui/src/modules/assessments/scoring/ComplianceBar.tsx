interface Props {
  percentage: number | null
}

function getBarColor(pct: number): string {
  if (pct < 34) return 'bg-error'
  if (pct < 67) return 'bg-warning'
  return 'bg-success'
}

export default function ComplianceBar({ percentage }: Props) {
  const displayValue = percentage != null ? `${percentage}%` : '—'
  const barWidth = percentage != null ? Math.min(100, Math.max(0, percentage)) : 0
  const colorClass = percentage != null ? getBarColor(percentage) : 'bg-base-300'

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-base-content/60">Overall Compliance</span>
        <span className="text-sm font-bold tabular-nums">{displayValue}</span>
      </div>
      <div
        className="w-full h-3 bg-base-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percentage ?? undefined}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Overall compliance percentage"
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  )
}
