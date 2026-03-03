import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Assessment, AssessmentStatus } from '@/types/assessment'
import { getAssessments } from '@/services/assessments'

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'completed', label: 'Completed' },
]

const LEVEL_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Levels' },
  { value: '1', label: 'Level 1' },
  { value: '2', label: 'Level 2' },
  { value: '3', label: 'Level 3' },
]

const STATUS_BADGE: Record<AssessmentStatus, string> = {
  draft: 'badge-ghost',
  in_progress: 'badge-info',
  under_review: 'badge-warning',
  completed: 'badge-success',
}

const STATUS_LABEL: Record<AssessmentStatus, string> = {
  draft: 'Draft',
  in_progress: 'In Progress',
  under_review: 'Under Review',
  completed: 'Completed',
}

const TYPE_LABEL: Record<string, string> = {
  self: 'Self',
  third_party: 'Third Party',
  government: 'Government',
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString()
}

export default function AssessmentListPage() {
  const navigate = useNavigate()
  const [assessments, setAssessments] = useState<Assessment[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [levelFilter, setLevelFilter] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const params: { status?: string; target_level?: number } = {}
    if (statusFilter) params.status = statusFilter
    if (levelFilter) params.target_level = Number(levelFilter)

    getAssessments(params)
      .then((data) => {
        if (!cancelled) {
          setAssessments(data.items)
          setTotal(data.total)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load assessments')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [statusFilter, levelFilter])

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Assessments</h1>
          <p className="text-base-content/60 text-sm mt-1">
            Manage CMMC compliance assessments
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/assessments/new')}
        >
          + New Assessment
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          className="select select-bordered select-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          className="select select-bordered select-sm"
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          aria-label="Filter by level"
        >
          {LEVEL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span className="text-sm text-base-content/60 self-center ml-auto">
          {total} assessment{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <span className="loading loading-spinner loading-lg" />
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && assessments.length === 0 && (
        <div className="text-center py-12 text-base-content/50">
          <p className="text-lg mb-2">No assessments found</p>
          <p className="text-sm">Create a new assessment to get started.</p>
        </div>
      )}

      {/* Table */}
      {!loading && assessments.length > 0 && (
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full">
            <thead>
              <tr>
                <th>Title</th>
                <th>Level</th>
                <th>Type</th>
                <th>Status</th>
                <th>SPRS</th>
                <th>Compliance</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {assessments.map((a) => (
                <tr
                  key={a.id}
                  className="cursor-pointer hover"
                  onClick={() => navigate(`/assessments/${a.id}`)}
                >
                  <td className="font-medium">{a.title}</td>
                  <td>
                    <span className="badge badge-outline badge-sm">
                      L{a.target_level}
                    </span>
                  </td>
                  <td className="text-sm">
                    {TYPE_LABEL[a.assessment_type] || a.assessment_type}
                  </td>
                  <td>
                    <span className={`badge badge-sm ${STATUS_BADGE[a.status]}`}>
                      {STATUS_LABEL[a.status] || a.status}
                    </span>
                  </td>
                  <td className="tabular-nums">
                    {a.sprs_score != null ? a.sprs_score : '—'}
                  </td>
                  <td className="tabular-nums">
                    {a.overall_score != null ? `${a.overall_score}%` : '—'}
                  </td>
                  <td className="text-sm text-base-content/60">
                    {formatDate(a.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
