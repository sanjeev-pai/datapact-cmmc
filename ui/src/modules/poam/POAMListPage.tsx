import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { POAM, POAMDetail, POAMStatus } from '@/types/poam'
import type { Assessment } from '@/types/assessment'
import {
  listPoams,
  getPoam,
  createPoam,
  deletePoam,
  activatePoam,
  completePoam,
  generateFromAssessment,
} from '@/services/poam'
import { getAssessments } from '@/services/assessments'
import { useAuth } from '@/hooks/useAuth'

const STATUS_BADGE: Record<POAMStatus, string> = {
  draft: 'badge-ghost',
  active: 'badge-info',
  completed: 'badge-success',
}

const STATUS_LABEL: Record<POAMStatus, string> = {
  draft: 'Draft',
  active: 'Active',
  completed: 'Completed',
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'completed', label: 'Completed' },
]

const MANAGE_ROLES = ['system_admin', 'org_admin', 'compliance_officer', 'assessor', 'c3pao_lead']

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  return new Date(dateStr).toLocaleDateString()
}

function countOverdue(detail: POAMDetail): number {
  const today = new Date().toISOString().slice(0, 10)
  return detail.items.filter(
    (item) =>
      item.status !== 'completed' &&
      item.scheduled_completion !== null &&
      item.scheduled_completion < today,
  ).length
}

export default function POAMListPage() {
  const { user, hasRole } = useAuth()
  const navigate = useNavigate()
  const canManage = hasRole(...MANAGE_ROLES)

  const [poams, setPoams] = useState<POAM[]>([])
  const [details, setDetails] = useState<Record<string, POAMDetail>>({})
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [assessmentFilter, setAssessmentFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [assessments, setAssessments] = useState<Assessment[]>([])

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [createData, setCreateData] = useState({ title: '', assessment_id: '' })
  const [saving, setSaving] = useState(false)

  // Generate modal
  const [showGenerate, setShowGenerate] = useState(false)
  const [generatePoamId, setGeneratePoamId] = useState('')
  const [generateAssessmentId, setGenerateAssessmentId] = useState('')
  const [generating, setGenerating] = useState(false)

  // Load assessments for dropdowns
  useEffect(() => {
    getAssessments()
      .then((data) => setAssessments(data.items))
      .catch(() => {})
  }, [])

  // Load POA&Ms
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const params: { assessment_id?: string; status?: string } = {}
    if (assessmentFilter) params.assessment_id = assessmentFilter
    if (statusFilter) params.status = statusFilter

    listPoams(params)
      .then(async (data) => {
        if (cancelled) return
        setPoams(data.items)
        setTotal(data.total)

        // Fetch details for item counts and overdue
        const detailMap: Record<string, POAMDetail> = {}
        const fetches = data.items.map((p) =>
          getPoam(p.id)
            .then((d) => { detailMap[p.id] = d })
            .catch(() => {}),
        )
        await Promise.all(fetches)
        if (!cancelled) setDetails(detailMap)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load POA&Ms')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [assessmentFilter, statusFilter])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!user?.org_id) return
    setSaving(true)
    setError(null)

    try {
      const created = await createPoam({
        org_id: user.org_id,
        title: createData.title,
        assessment_id: createData.assessment_id || undefined,
      })
      setPoams((prev) => [created, ...prev])
      setTotal((t) => t + 1)
      // Fetch detail for the new POAM
      getPoam(created.id)
        .then((d) => setDetails((prev) => ({ ...prev, [created.id]: d })))
        .catch(() => {})
      setShowCreate(false)
      setCreateData({ title: '', assessment_id: '' })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Create failed'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    try {
      await deletePoam(id)
      setPoams((prev) => prev.filter((p) => p.id !== id))
      setTotal((t) => t - 1)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed'
      setError(msg)
    }
  }

  async function handleActivate(id: string) {
    try {
      const updated = await activatePoam(id)
      setPoams((prev) => prev.map((p) => (p.id === id ? updated : p)))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Activate failed'
      setError(msg)
    }
  }

  async function handleComplete(id: string) {
    try {
      const updated = await completePoam(id)
      setPoams((prev) => prev.map((p) => (p.id === id ? updated : p)))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Complete failed'
      setError(msg)
    }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (!generatePoamId || !generateAssessmentId) return
    setGenerating(true)
    setError(null)

    try {
      const items = await generateFromAssessment(generatePoamId, generateAssessmentId)
      // Refresh detail for that POA&M
      const detail = await getPoam(generatePoamId)
      setDetails((prev) => ({ ...prev, [generatePoamId]: detail }))
      setShowGenerate(false)
      setGeneratePoamId('')
      setGenerateAssessmentId('')
      if (items.length === 0) {
        setError('No unresolved findings found for this assessment.')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Generation failed'
      setError(msg)
    } finally {
      setGenerating(false)
    }
  }

  function getAssessmentTitle(assessmentId: string | null): string {
    if (!assessmentId) return '\u2014'
    const a = assessments.find((x) => x.id === assessmentId)
    return a ? a.title : assessmentId.slice(0, 8)
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">POA&M</h1>
          <p className="text-base-content/60 text-sm mt-1">
            Plans of Action and Milestones for remediation tracking
          </p>
        </div>
        {canManage && (
          <div className="flex gap-2">
            <button
              className="btn btn-outline btn-sm"
              onClick={() => setShowGenerate(true)}
            >
              Generate from Assessment
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => {
                setCreateData({ title: '', assessment_id: assessmentFilter })
                setShowCreate(true)
              }}
            >
              + New POA&M
            </button>
          </div>
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
          {total} POA&M{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
        </div>
      )}

      {/* Create Form */}
      {showCreate && (
        <div className="card bg-base-100 shadow mb-6">
          <div className="card-body">
            <h2 className="card-title text-lg">New POA&M</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Title *</span>
                  </label>
                  <input
                    type="text"
                    className="input input-bordered input-sm"
                    value={createData.title}
                    onChange={(e) => setCreateData({ ...createData, title: e.target.value })}
                    required
                    maxLength={256}
                  />
                </div>
                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Assessment (optional)</span>
                  </label>
                  <select
                    className="select select-bordered select-sm"
                    value={createData.assessment_id}
                    onChange={(e) => setCreateData({ ...createData, assessment_id: e.target.value })}
                  >
                    <option value="">None</option>
                    {assessments.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
                  {saving ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Generate Modal */}
      {showGenerate && (
        <div className="card bg-base-100 shadow mb-6">
          <div className="card-body">
            <h2 className="card-title text-lg">Generate POA&M Items from Assessment</h2>
            <p className="text-sm text-base-content/60 mb-2">
              Auto-create items from unresolved findings in an assessment.
            </p>
            <form onSubmit={handleGenerate} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Target POA&M *</span>
                  </label>
                  <select
                    className="select select-bordered select-sm"
                    value={generatePoamId}
                    onChange={(e) => setGeneratePoamId(e.target.value)}
                    required
                  >
                    <option value="">Select POA&M...</option>
                    {poams
                      .filter((p) => p.status !== 'completed')
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.title}
                        </option>
                      ))}
                  </select>
                </div>
                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Source Assessment *</span>
                  </label>
                  <select
                    className="select select-bordered select-sm"
                    value={generateAssessmentId}
                    onChange={(e) => setGenerateAssessmentId(e.target.value)}
                    required
                  >
                    <option value="">Select assessment...</option>
                    {assessments.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowGenerate(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={generating}>
                  {generating ? 'Generating...' : 'Generate Items'}
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
      {!loading && !error && poams.length === 0 && (
        <div className="text-center py-12 text-base-content/50">
          <p className="text-lg mb-2">No POA&Ms found</p>
          <p className="text-sm">
            Create a POA&M to track remediation plans, or generate items from assessment findings.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && poams.length > 0 && (
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full">
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Assessment</th>
                <th>Items</th>
                <th>Overdue</th>
                <th>Created</th>
                {canManage && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {poams.map((p) => {
                const detail = details[p.id]
                const itemCount = detail ? detail.items.length : '\u2014'
                const overdueCount = detail ? countOverdue(detail) : 0
                return (
                  <tr
                    key={p.id}
                    className="cursor-pointer hover"
                    onClick={() => navigate(`/poams/${p.id}`)}
                  >
                    <td>
                      <div className="font-medium">{p.title}</div>
                    </td>
                    <td>
                      <span className={`badge badge-sm ${STATUS_BADGE[p.status as POAMStatus]}`}>
                        {STATUS_LABEL[p.status as POAMStatus] || p.status}
                      </span>
                    </td>
                    <td className="text-sm text-base-content/60">
                      {getAssessmentTitle(p.assessment_id)}
                    </td>
                    <td className="text-sm">{itemCount}</td>
                    <td>
                      {overdueCount > 0 ? (
                        <span className="badge badge-sm badge-error">{overdueCount}</span>
                      ) : (
                        <span className="text-sm text-base-content/40">0</span>
                      )}
                    </td>
                    <td className="text-sm text-base-content/60">{formatDate(p.created_at)}</td>
                    {canManage && (
                      <td>
                        <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                          {p.status === 'draft' && (
                            <button
                              className="btn btn-ghost btn-xs"
                              onClick={() => handleActivate(p.id)}
                            >
                              Activate
                            </button>
                          )}
                          {p.status === 'active' && (
                            <button
                              className="btn btn-ghost btn-xs"
                              onClick={() => handleComplete(p.id)}
                            >
                              Complete
                            </button>
                          )}
                          {p.status === 'draft' && (
                            <button
                              className="btn btn-ghost btn-xs text-error"
                              onClick={() => handleDelete(p.id)}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
