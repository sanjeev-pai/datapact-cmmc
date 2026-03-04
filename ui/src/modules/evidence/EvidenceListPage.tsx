import { useEffect, useState } from 'react'
import type { Evidence, ReviewStatus } from '@/types/evidence'
import type { Assessment } from '@/types/assessment'
import { listEvidence, reviewEvidence, deleteEvidence, getDownloadUrl } from '@/services/evidence'
import { getAssessments } from '@/services/assessments'
import { useAuth } from '@/hooks/useAuth'
import { useOrg } from '@/hooks/useOrg'

const STATUS_BADGE: Record<ReviewStatus, string> = {
  pending: 'badge-ghost',
  accepted: 'badge-success',
  rejected: 'badge-error',
}

const STATUS_LABEL: Record<ReviewStatus, string> = {
  pending: 'Pending',
  accepted: 'Accepted',
  rejected: 'Rejected',
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'rejected', label: 'Rejected' },
]

const REVIEW_ROLES = ['system_admin', 'org_admin', 'assessor', 'c3pao_lead']

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  return new Date(dateStr).toLocaleDateString()
}

export default function EvidenceListPage() {
  const { hasRole } = useAuth()
  const { effectiveOrgId } = useOrg()
  const canReview = hasRole(...REVIEW_ROLES)

  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [assessmentFilter, setAssessmentFilter] = useState('')
  const [assessments, setAssessments] = useState<Assessment[]>([])

  // Load assessments for filter dropdown (scoped by org)
  useEffect(() => {
    const params: { org_id?: string } = {}
    if (effectiveOrgId) params.org_id = effectiveOrgId
    getAssessments(params)
      .then((data) => setAssessments(data.items))
      .catch(() => {})
  }, [effectiveOrgId])

  // Load evidence
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const params: { review_status?: string; assessment_id?: string; org_id?: string } = {}
    if (statusFilter) params.review_status = statusFilter
    if (assessmentFilter) params.assessment_id = assessmentFilter
    if (effectiveOrgId) params.org_id = effectiveOrgId

    listEvidence(params)
      .then((data) => {
        if (!cancelled) {
          setEvidence(data.items)
          setTotal(data.total)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load evidence')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [statusFilter, assessmentFilter, effectiveOrgId])

  async function handleReview(id: string, status: 'accepted' | 'rejected') {
    try {
      const updated = await reviewEvidence(id, status)
      setEvidence((prev) =>
        prev.map((ev) => (ev.id === updated.id ? updated : ev)),
      )
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Review failed'
      setError(msg)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteEvidence(id)
      setEvidence((prev) => prev.filter((ev) => ev.id !== id))
      setTotal((t) => t - 1)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed'
      setError(msg)
    }
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Evidence</h1>
          <p className="text-base-content/60 text-sm mt-1">
            Browse and review evidence across all assessments
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select
          className="select select-bordered select-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by review status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          className="select select-bordered select-sm"
          value={assessmentFilter}
          onChange={(e) => setAssessmentFilter(e.target.value)}
          aria-label="Filter by assessment"
        >
          <option value="">All Assessments</option>
          {assessments.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
        <span className="text-sm text-base-content/60 self-center ml-auto">
          {total} item{total !== 1 ? 's' : ''}
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
      {!loading && !error && evidence.length === 0 && (
        <div className="text-center py-12 text-base-content/50">
          <p className="text-lg mb-2">No evidence found</p>
          <p className="text-sm">
            Upload evidence from within an assessment workspace.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && evidence.length > 0 && (
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full">
            <thead>
              <tr>
                <th>Title</th>
                <th>File</th>
                <th>Size</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Reviewed</th>
                {canReview && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {evidence.map((ev) => (
                <tr key={ev.id}>
                  <td>
                    <div className="font-medium">{ev.title}</div>
                    {ev.description && (
                      <div className="text-xs text-base-content/50 truncate max-w-xs">
                        {ev.description}
                      </div>
                    )}
                  </td>
                  <td>
                    {ev.file_name ? (
                      <a
                        href={getDownloadUrl(ev.id)}
                        className="link link-primary text-sm"
                        target="_blank"
                        rel="noopener noreferrer"
                        title={ev.file_name}
                      >
                        {ev.file_name}
                      </a>
                    ) : (
                      <span className="text-base-content/40 text-sm">No file</span>
                    )}
                  </td>
                  <td className="text-sm tabular-nums">
                    {ev.file_size ? formatSize(ev.file_size) : '\u2014'}
                  </td>
                  <td>
                    <span
                      className={`badge badge-sm ${STATUS_BADGE[ev.review_status as ReviewStatus]}`}
                    >
                      {STATUS_LABEL[ev.review_status as ReviewStatus] || ev.review_status}
                    </span>
                  </td>
                  <td className="text-sm text-base-content/60">
                    {formatDate(ev.created_at)}
                  </td>
                  <td className="text-sm text-base-content/60">
                    {formatDate(ev.reviewed_at)}
                  </td>
                  {canReview && (
                    <td>
                      {ev.review_status === 'pending' ? (
                        <div className="flex gap-1">
                          <button
                            className="btn btn-success btn-xs"
                            onClick={() => handleReview(ev.id, 'accepted')}
                          >
                            Accept
                          </button>
                          <button
                            className="btn btn-error btn-xs btn-outline"
                            onClick={() => handleReview(ev.id, 'rejected')}
                          >
                            Reject
                          </button>
                        </div>
                      ) : (
                        <button
                          className="btn btn-ghost btn-xs text-error"
                          onClick={() => handleDelete(ev.id)}
                          disabled={ev.review_status !== 'pending'}
                          title="Only pending evidence can be deleted"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
