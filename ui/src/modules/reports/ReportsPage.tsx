import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { getAssessments } from '@/services/assessments'
import { downloadAssessmentReport, downloadSprsReport } from '@/services/reports'
import type { Assessment } from '@/types/assessment'

type ReportFormat = 'pdf' | 'csv'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
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

export default function ReportsPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''

  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Download state
  const [downloading, setDownloading] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  // Selected assessment for download
  const [selectedId, setSelectedId] = useState<string>('')
  const [format, setFormat] = useState<ReportFormat>('pdf')

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    getAssessments()
      .then((res) => {
        if (cancelled) return
        setAssessments(res.items)
        // Default-select first completed assessment (or first overall)
        const completed = res.items.find((a) => a.status === 'completed')
        if (completed) setSelectedId(completed.id)
        else if (res.items.length > 0) setSelectedId(res.items[0].id)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load assessments')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  async function handleDownloadAssessment() {
    if (!selectedId) return
    setDownloading('assessment')
    setDownloadError(null)
    try {
      await downloadAssessmentReport(selectedId, format)
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloading(null)
    }
  }

  async function handleDownloadSprs() {
    if (!orgId) return
    setDownloading('sprs')
    setDownloadError(null)
    try {
      await downloadSprsReport(orgId)
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setDownloading(null)
    }
  }

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
        <div className="alert alert-error"><span>{error}</span></div>
      </div>
    )
  }

  const selected = assessments.find((a) => a.id === selectedId)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Reports</h1>
        <p className="text-sm text-base-content/60 mt-1">
          Download assessment and SPRS reports
        </p>
      </div>

      {downloadError && (
        <div className="alert alert-error">
          <span>{downloadError}</span>
          <button className="btn btn-ghost btn-xs" onClick={() => setDownloadError(null)}>
            Dismiss
          </button>
        </div>
      )}

      {/* Assessment Report Card */}
      <div className="card bg-base-100 shadow-sm border border-base-200">
        <div className="card-body">
          <h2 className="card-title text-lg">Assessment Report</h2>
          <p className="text-sm text-base-content/60">
            Download a detailed report for a specific assessment including practice
            evaluations, domain breakdown, and SPRS score.
          </p>

          {assessments.length === 0 ? (
            <div className="alert alert-info mt-4">
              <span>No assessments available. Create an assessment first.</span>
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              {/* Assessment selector */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Select Assessment</span>
                </label>
                <select
                  className="select select-bordered"
                  value={selectedId}
                  onChange={(e) => setSelectedId(e.target.value)}
                >
                  {assessments.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title} — L{a.target_level} ({a.status.replace('_', ' ')})
                    </option>
                  ))}
                </select>
              </div>

              {/* Selected assessment summary */}
              {selected && (
                <div className="bg-base-200 rounded-lg p-4 text-sm space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{selected.title}</span>
                    {statusBadge(selected.status)}
                  </div>
                  <div className="text-base-content/60 flex flex-wrap gap-x-4">
                    <span>Level {selected.target_level}</span>
                    <span>Type: {selected.assessment_type}</span>
                    {selected.overall_score != null && (
                      <span>Score: {Math.round(selected.overall_score)}%</span>
                    )}
                    {selected.sprs_score != null && (
                      <span>SPRS: {selected.sprs_score}</span>
                    )}
                    <span>Created: {formatDate(selected.created_at)}</span>
                    {selected.completed_at && (
                      <span>Completed: {formatDate(selected.completed_at)}</span>
                    )}
                  </div>
                </div>
              )}

              {/* Format picker + download */}
              <div className="flex items-end gap-3">
                <div className="form-control">
                  <label className="label">
                    <span className="label-text font-medium">Format</span>
                  </label>
                  <select
                    className="select select-bordered select-sm"
                    value={format}
                    onChange={(e) => setFormat(e.target.value as ReportFormat)}
                  >
                    <option value="pdf">PDF</option>
                    <option value="csv">CSV</option>
                  </select>
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={!selectedId || downloading === 'assessment'}
                  onClick={handleDownloadAssessment}
                >
                  {downloading === 'assessment' ? (
                    <span className="loading loading-spinner loading-xs" />
                  ) : (
                    'Download Report'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SPRS Report Card */}
      {orgId && (
        <div className="card bg-base-100 shadow-sm border border-base-200">
          <div className="card-body">
            <h2 className="card-title text-lg">SPRS Score Report</h2>
            <p className="text-sm text-base-content/60">
              Download the SPRS score history for your organization as CSV.
            </p>
            <div className="mt-4">
              <button
                className="btn btn-primary btn-sm"
                disabled={downloading === 'sprs'}
                onClick={handleDownloadSprs}
              >
                {downloading === 'sprs' ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  'Download SPRS Report (CSV)'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assessment list reference */}
      <div className="card bg-base-100 shadow-sm border border-base-200">
        <div className="card-body">
          <h2 className="card-title text-lg">All Assessments</h2>
          <div className="overflow-x-auto">
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Level</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th className="text-right">Score</th>
                  <th className="text-right">SPRS</th>
                  <th className="text-right">Date</th>
                </tr>
              </thead>
              <tbody>
                {assessments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center text-base-content/50">
                      No assessments
                    </td>
                  </tr>
                ) : (
                  assessments.map((a) => (
                    <tr
                      key={a.id}
                      className={`hover cursor-pointer ${a.id === selectedId ? 'bg-primary/5' : ''}`}
                      onClick={() => setSelectedId(a.id)}
                    >
                      <td className="font-medium">{a.title}</td>
                      <td>L{a.target_level}</td>
                      <td>{a.assessment_type}</td>
                      <td>{statusBadge(a.status)}</td>
                      <td className="text-right tabular-nums">
                        {a.overall_score != null ? `${Math.round(a.overall_score)}%` : '—'}
                      </td>
                      <td className="text-right tabular-nums">
                        {a.sprs_score != null ? a.sprs_score : '—'}
                      </td>
                      <td className="text-right text-xs">
                        {formatDate(a.completed_at || a.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
