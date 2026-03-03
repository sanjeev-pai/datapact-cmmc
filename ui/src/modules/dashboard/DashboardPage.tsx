import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
} from 'recharts'
import { useAuth } from '@/hooks/useAuth'
import {
  getComplianceSummary,
  getDomainCompliance,
  getSprsHistory,
  getTimeline,
} from '@/services/dashboard'
import type {
  ComplianceSummary,
  DomainCompliance,
  SprsSummary,
  TimelineEntry,
} from '@/types/dashboard'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function complianceColor(pct: number): string {
  if (pct < 34) return '#ef4444'
  if (pct < 67) return '#f59e0b'
  return '#22c55e'
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    draft: 'badge-ghost',
    in_progress: 'badge-info',
    under_review: 'badge-warning',
    completed: 'badge-success',
  }
  return (
    <span className={`badge badge-sm ${map[status] ?? 'badge-ghost'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ComplianceLevelCard({
  level,
  percentage,
}: {
  level: string
  percentage: number | null
}) {
  const pct = percentage ?? 0
  const display = percentage != null ? `${Math.round(percentage)}%` : '—'
  const color = percentage != null ? complianceColor(pct) : '#d1d5db'

  return (
    <div className="card bg-base-100 shadow-sm border border-base-200">
      <div className="card-body p-4">
        <h3 className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
          {level}
        </h3>
        <div className="flex items-end gap-2 mt-1">
          <span className="text-3xl font-bold tabular-nums" style={{ color }}>
            {display}
          </span>
        </div>
        <div className="w-full h-2 bg-base-200 rounded-full overflow-hidden mt-2">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: color }}
          />
        </div>
      </div>
    </div>
  )
}

function SprsCard({ summary }: { summary: SprsSummary | null }) {
  if (!summary) return null
  const score = summary.current
  const color =
    score == null
      ? '#d1d5db'
      : score < -50
        ? '#ef4444'
        : score <= 0
          ? '#f97316'
          : score <= 54
            ? '#eab308'
            : '#22c55e'

  return (
    <div className="card bg-base-100 shadow-sm border border-base-200">
      <div className="card-body p-4">
        <h3 className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
          SPRS Score
        </h3>
        <span className="text-3xl font-bold tabular-nums mt-1" style={{ color }}>
          {score != null ? score : '—'}
        </span>
        <span className="text-xs text-base-content/50">
          Range: -203 to 110
        </span>
      </div>
    </div>
  )
}

function SprsHistoryChart({ summary }: { summary: SprsSummary | null }) {
  if (!summary || summary.history.length === 0) return null

  const data = [...summary.history].reverse().map((h) => ({
    name: h.title.length > 20 ? h.title.slice(0, 20) + '...' : h.title,
    score: h.sprs_score,
    date: formatDate(h.date),
  }))

  return (
    <div className="card bg-base-100 shadow-sm border border-base-200">
      <div className="card-body p-4">
        <h3 className="text-sm font-semibold mb-3">SPRS Score History</h3>
        {data.length < 2 ? (
          <p className="text-sm text-base-content/50">
            Need at least 2 assessments to show trend.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis domain={[-203, 110]} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#6366f1"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

function DomainHeatMap({ domains }: { domains: DomainCompliance[] }) {
  if (domains.length === 0) return null

  return (
    <div className="card bg-base-100 shadow-sm border border-base-200">
      <div className="card-body p-4">
        <h3 className="text-sm font-semibold mb-3">Domain Compliance</h3>
        <ResponsiveContainer width="100%" height={Math.max(180, domains.length * 32)}>
          <BarChart data={domains} layout="vertical" margin={{ left: 8, right: 16 }}>
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
            <YAxis
              type="category"
              dataKey="domain_name"
              width={140}
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              formatter={(value) => [`${value}%`, 'Compliance']}
            />
            <Bar
              dataKey="percentage"
              radius={[0, 4, 4, 0]}
              fill="#6366f1"
              barSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function AssessmentTimeline({ entries }: { entries: TimelineEntry[] }) {
  if (entries.length === 0) {
    return (
      <div className="card bg-base-100 shadow-sm border border-base-200">
        <div className="card-body p-4">
          <h3 className="text-sm font-semibold mb-2">Recent Assessments</h3>
          <p className="text-sm text-base-content/50">No assessments yet.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card bg-base-100 shadow-sm border border-base-200">
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">Recent Assessments</h3>
          <Link to="/assessments" className="text-xs link link-primary">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Title</th>
                <th>Level</th>
                <th>Status</th>
                <th className="text-right">Score</th>
                <th className="text-right">Date</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="hover">
                  <td>
                    <Link
                      to={`/assessments/${e.id}`}
                      className="link link-hover"
                    >
                      {e.title}
                    </Link>
                  </td>
                  <td>L{e.target_level}</td>
                  <td>{statusBadge(e.status)}</td>
                  <td className="text-right tabular-nums">
                    {e.overall_score != null
                      ? `${Math.round(e.overall_score)}%`
                      : '—'}
                  </td>
                  <td className="text-right text-xs">
                    {formatDate(e.completed_at || e.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''

  const [compliance, setCompliance] = useState<ComplianceSummary | null>(null)
  const [sprsSummary, setSprsSummary] = useState<SprsSummary | null>(null)
  const [domains, setDomains] = useState<DomainCompliance[]>([])
  const [timeline, setTimeline] = useState<TimelineEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Selected assessment for domain breakdown
  const [selectedAssessmentId, setSelectedAssessmentId] = useState<string | null>(null)

  useEffect(() => {
    if (!orgId) return
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [comp, sprs, tl] = await Promise.all([
          getComplianceSummary(),
          getSprsHistory(orgId),
          getTimeline(orgId),
        ])
        if (cancelled) return
        setCompliance(comp)
        setSprsSummary(sprs)
        setTimeline(tl)

        // Auto-select most recent completed assessment for domain view
        const completed = tl.find((a) => a.status === 'completed')
        if (completed) {
          setSelectedAssessmentId(completed.id)
        } else if (tl.length > 0) {
          setSelectedAssessmentId(tl[0].id)
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load dashboard')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [orgId])

  // Load domain compliance when selectedAssessmentId changes
  useEffect(() => {
    if (!selectedAssessmentId) return
    let cancelled = false

    getDomainCompliance(selectedAssessmentId)
      .then((d) => {
        if (!cancelled) setDomains(d)
      })
      .catch(() => {
        if (!cancelled) setDomains([])
      })

    return () => {
      cancelled = true
    }
  }, [selectedAssessmentId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="loading loading-spinner loading-lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="alert alert-error">
          <span>{error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-base-content/60 mt-1">
          CMMC compliance overview for your organization
        </p>
      </div>

      {/* Compliance summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <ComplianceLevelCard
          level="Level 1"
          percentage={compliance?.level_1 ?? null}
        />
        <ComplianceLevelCard
          level="Level 2"
          percentage={compliance?.level_2 ?? null}
        />
        <ComplianceLevelCard
          level="Level 3"
          percentage={compliance?.level_3 ?? null}
        />
        <SprsCard summary={sprsSummary} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Domain heat map with assessment selector */}
        <div>
          {timeline.length > 1 && (
            <div className="mb-2">
              <select
                className="select select-bordered select-sm"
                value={selectedAssessmentId ?? ''}
                onChange={(e) => setSelectedAssessmentId(e.target.value)}
              >
                {timeline.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.title} (L{a.target_level})
                  </option>
                ))}
              </select>
            </div>
          )}
          <DomainHeatMap domains={domains} />
        </div>

        {/* SPRS history */}
        <SprsHistoryChart summary={sprsSummary} />
      </div>

      {/* Assessment timeline table */}
      <AssessmentTimeline entries={timeline} />
    </div>
  )
}
