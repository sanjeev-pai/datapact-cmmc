import { useEffect, useState } from 'react'
import type { Finding, FindingType, FindingSeverity, FindingStatus } from '@/types/finding'
import type { Assessment } from '@/types/assessment'
import { listFindings, createFinding, updateFinding, deleteFinding } from '@/services/findings'
import { getAssessments } from '@/services/assessments'
import { useAuth } from '@/hooks/useAuth'
import { useOrg } from '@/hooks/useOrg'

const SEVERITY_BADGE: Record<FindingSeverity, string> = {
  high: 'badge-error',
  medium: 'badge-warning',
  low: 'badge-info',
}

const STATUS_BADGE: Record<FindingStatus, string> = {
  open: 'badge-ghost',
  resolved: 'badge-success',
  accepted_risk: 'badge-warning',
}

const STATUS_LABEL: Record<FindingStatus, string> = {
  open: 'Open',
  resolved: 'Resolved',
  accepted_risk: 'Accepted Risk',
}

const TYPE_LABEL: Record<FindingType, string> = {
  deficiency: 'Deficiency',
  observation: 'Observation',
  recommendation: 'Recommendation',
}

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'deficiency', label: 'Deficiency' },
  { value: 'observation', label: 'Observation' },
  { value: 'recommendation', label: 'Recommendation' },
]

const SEVERITY_OPTIONS = [
  { value: '', label: 'All Severities' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'accepted_risk', label: 'Accepted Risk' },
]

const MANAGE_ROLES = ['system_admin', 'org_admin', 'compliance_officer', 'assessor', 'c3pao_lead']

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  return new Date(dateStr).toLocaleDateString()
}

export default function FindingsPage() {
  const { hasRole } = useAuth()
  const { effectiveOrgId } = useOrg()
  const canManage = hasRole(...MANAGE_ROLES)

  const [findings, setFindings] = useState<Finding[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [assessmentFilter, setAssessmentFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [assessments, setAssessments] = useState<Assessment[]>([])

  // Create/Edit form
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    assessment_id: '',
    practice_id: '',
    finding_type: 'deficiency' as string,
    severity: 'medium' as string,
    title: '',
    description: '',
    status: 'open' as string,
  })
  const [saving, setSaving] = useState(false)

  // Load assessments for filter and form dropdowns (scoped by org)
  useEffect(() => {
    const params: { org_id?: string } = {}
    if (effectiveOrgId) params.org_id = effectiveOrgId
    getAssessments(params)
      .then((data) => setAssessments(data.items))
      .catch(() => {})
  }, [effectiveOrgId])

  // Load findings
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const params: { assessment_id?: string; type?: string; severity?: string; status?: string; org_id?: string } = {}
    if (assessmentFilter) params.assessment_id = assessmentFilter
    if (typeFilter) params.type = typeFilter
    if (severityFilter) params.severity = severityFilter
    if (statusFilter) params.status = statusFilter
    if (effectiveOrgId) params.org_id = effectiveOrgId

    listFindings(params)
      .then((data) => {
        if (!cancelled) {
          setFindings(data.items)
          setTotal(data.total)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load findings')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [assessmentFilter, typeFilter, severityFilter, statusFilter, effectiveOrgId])

  function openCreate() {
    setEditingId(null)
    setFormData({
      assessment_id: assessmentFilter || '',
      practice_id: '',
      finding_type: 'deficiency',
      severity: 'medium',
      title: '',
      description: '',
      status: 'open',
    })
    setShowForm(true)
  }

  function openEdit(f: Finding) {
    setEditingId(f.id)
    setFormData({
      assessment_id: f.assessment_id,
      practice_id: f.practice_id || '',
      finding_type: f.finding_type,
      severity: f.severity,
      title: f.title,
      description: f.description || '',
      status: f.status,
    })
    setShowForm(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      if (editingId) {
        const updated = await updateFinding(editingId, {
          practice_id: formData.practice_id || undefined,
          finding_type: formData.finding_type,
          severity: formData.severity,
          title: formData.title,
          description: formData.description || undefined,
          status: formData.status,
        })
        setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)))
      } else {
        const created = await createFinding({
          assessment_id: formData.assessment_id,
          practice_id: formData.practice_id || undefined,
          finding_type: formData.finding_type,
          severity: formData.severity,
          title: formData.title,
          description: formData.description || undefined,
        })
        setFindings((prev) => [created, ...prev])
        setTotal((t) => t + 1)
      }
      setShowForm(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Save failed'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteFinding(id)
      setFindings((prev) => prev.filter((f) => f.id !== id))
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
          <h1 className="text-2xl font-bold">Findings</h1>
          <p className="text-base-content/60 text-sm mt-1">
            Assessment findings — deficiencies, observations, and recommendations
          </p>
        </div>
        {canManage && (
          <button className="btn btn-primary btn-sm" onClick={openCreate}>
            + New Finding
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
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
        <select
          className="select select-bordered select-sm"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by type"
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          className="select select-bordered select-sm"
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          aria-label="Filter by severity"
        >
          {SEVERITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
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
        <span className="text-sm text-base-content/60 self-center ml-auto">
          {total} finding{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
        </div>
      )}

      {/* Create/Edit Form */}
      {showForm && (
        <div className="card bg-base-100 shadow mb-6">
          <div className="card-body">
            <h2 className="card-title text-lg">
              {editingId ? 'Edit Finding' : 'New Finding'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {!editingId && (
                  <div className="form-control">
                    <label className="label"><span className="label-text">Assessment *</span></label>
                    <select
                      className="select select-bordered select-sm"
                      value={formData.assessment_id}
                      onChange={(e) => setFormData({ ...formData, assessment_id: e.target.value })}
                      required
                    >
                      <option value="">Select assessment...</option>
                      {assessments.map((a) => (
                        <option key={a.id} value={a.id}>{a.title}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="form-control">
                  <label className="label"><span className="label-text">Title *</span></label>
                  <input
                    type="text"
                    className="input input-bordered input-sm"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    required
                    maxLength={256}
                  />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Practice ID</span></label>
                  <input
                    type="text"
                    className="input input-bordered input-sm"
                    value={formData.practice_id}
                    onChange={(e) => setFormData({ ...formData, practice_id: e.target.value })}
                    placeholder="e.g. AC.L2-3.1.1"
                    maxLength={32}
                  />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Type</span></label>
                  <select
                    className="select select-bordered select-sm"
                    value={formData.finding_type}
                    onChange={(e) => setFormData({ ...formData, finding_type: e.target.value })}
                  >
                    <option value="deficiency">Deficiency</option>
                    <option value="observation">Observation</option>
                    <option value="recommendation">Recommendation</option>
                  </select>
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Severity</span></label>
                  <select
                    className="select select-bordered select-sm"
                    value={formData.severity}
                    onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
                {editingId && (
                  <div className="form-control">
                    <label className="label"><span className="label-text">Status</span></label>
                    <select
                      className="select select-bordered select-sm"
                      value={formData.status}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    >
                      <option value="open">Open</option>
                      <option value="resolved">Resolved</option>
                      <option value="accepted_risk">Accepted Risk</option>
                    </select>
                  </div>
                )}
              </div>
              <div className="form-control">
                <label className="label"><span className="label-text">Description</span></label>
                <textarea
                  className="textarea textarea-bordered textarea-sm"
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={saving}
                >
                  {saving ? 'Saving...' : editingId ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <span className="loading loading-spinner loading-lg" />
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && findings.length === 0 && (
        <div className="text-center py-12 text-base-content/50">
          <p className="text-lg mb-2">No findings found</p>
          <p className="text-sm">
            Create findings during assessment review or use the button above.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && findings.length > 0 && (
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full">
            <thead>
              <tr>
                <th>Title</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Practice</th>
                <th>Created</th>
                {canManage && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id}>
                  <td>
                    <div className="font-medium">{f.title}</div>
                    {f.description && (
                      <div className="text-xs text-base-content/50 truncate max-w-xs">
                        {f.description}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className="text-sm">
                      {TYPE_LABEL[f.finding_type] || f.finding_type}
                    </span>
                  </td>
                  <td>
                    <span className={`badge badge-sm ${SEVERITY_BADGE[f.severity]}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`badge badge-sm ${STATUS_BADGE[f.status]}`}>
                      {STATUS_LABEL[f.status] || f.status}
                    </span>
                  </td>
                  <td className="text-sm text-base-content/60">
                    {f.practice_id || '\u2014'}
                  </td>
                  <td className="text-sm text-base-content/60">
                    {formatDate(f.created_at)}
                  </td>
                  {canManage && (
                    <td>
                      <div className="flex gap-1">
                        <button
                          className="btn btn-ghost btn-xs"
                          onClick={() => openEdit(f)}
                        >
                          Edit
                        </button>
                        {f.status === 'open' && (
                          <button
                            className="btn btn-ghost btn-xs text-error"
                            onClick={() => handleDelete(f.id)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
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
