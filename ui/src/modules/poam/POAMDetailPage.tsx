import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import type { POAMDetail, POAMItem, POAMItemStatus, POAMStatus } from '@/types/poam'
import {
  getPoam,
  updatePoam,
  activatePoam,
  completePoam,
  addPoamItem,
  updatePoamItem,
  removePoamItem,
} from '@/services/poam'
import { useAuth } from '@/hooks/useAuth'

const MANAGE_ROLES = ['system_admin', 'org_admin', 'compliance_officer', 'assessor', 'c3pao_lead']

const STATUS_BADGE: Record<POAMStatus, string> = {
  draft: 'badge-ghost',
  active: 'badge-info',
  completed: 'badge-success',
}

const ITEM_STATUS_BADGE: Record<POAMItemStatus, string> = {
  open: 'badge-ghost',
  in_progress: 'badge-info',
  completed: 'badge-success',
}

const ITEM_STATUS_LABEL: Record<POAMItemStatus, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  completed: 'Completed',
}

function isOverdue(item: POAMItem): boolean {
  if (item.status === 'completed' || !item.scheduled_completion) return false
  return item.scheduled_completion < new Date().toISOString().slice(0, 10)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  return new Date(dateStr).toLocaleDateString()
}

function exportCsv(poam: POAMDetail) {
  const headers = [
    'Milestone',
    'Practice ID',
    'Status',
    'Scheduled Completion',
    'Actual Completion',
    'Resources Required',
    'Risk Accepted',
    'Finding ID',
  ]
  const rows = poam.items.map((item) => [
    item.milestone || '',
    item.practice_id || '',
    item.status,
    item.scheduled_completion || '',
    item.actual_completion || '',
    item.resources_required || '',
    item.risk_accepted ? 'Yes' : 'No',
    item.finding_id || '',
  ])

  const csvContent = [
    `# POA&M: ${poam.title}`,
    `# Status: ${poam.status}`,
    `# Exported: ${new Date().toISOString()}`,
    '',
    headers.join(','),
    ...rows.map((r) => r.map((v) => `"${v.replace(/"/g, '""')}"`).join(',')),
  ].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `poam-${poam.title.replace(/\s+/g, '-').toLowerCase()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function POAMDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { hasRole } = useAuth()
  const canManage = hasRole(...MANAGE_ROLES)

  const [poam, setPoam] = useState<POAMDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Inline edit
  const [editingItemId, setEditingItemId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({
    milestone: '',
    scheduled_completion: '',
    resources_required: '',
    status: '' as string,
    risk_accepted: false,
  })
  const [saving, setSaving] = useState(false)

  // Add item form
  const [showAddForm, setShowAddForm] = useState(false)
  const [addForm, setAddForm] = useState({
    practice_id: '',
    milestone: '',
    scheduled_completion: '',
    resources_required: '',
    risk_accepted: false,
  })
  const [adding, setAdding] = useState(false)

  // Title edit
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleValue, setTitleValue] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getPoam(id)
      .then(setPoam)
      .catch((err) => setError(err.message || 'Failed to load POA&M'))
      .finally(() => setLoading(false))
  }, [id])

  function openEditItem(item: POAMItem) {
    setEditingItemId(item.id)
    setEditForm({
      milestone: item.milestone || '',
      scheduled_completion: item.scheduled_completion || '',
      resources_required: item.resources_required || '',
      status: item.status,
      risk_accepted: item.risk_accepted,
    })
  }

  async function handleSaveItem(e: React.FormEvent) {
    e.preventDefault()
    if (!editingItemId || !poam) return
    setSaving(true)
    setError(null)
    try {
      const updated = await updatePoamItem(poam.id, editingItemId, {
        milestone: editForm.milestone || undefined,
        scheduled_completion: editForm.scheduled_completion || null,
        resources_required: editForm.resources_required || null,
        status: editForm.status,
        risk_accepted: editForm.risk_accepted,
      })
      setPoam({ ...poam, items: poam.items.map((i) => (i.id === updated.id ? updated : i)) })
      setEditingItemId(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleAddItem(e: React.FormEvent) {
    e.preventDefault()
    if (!poam) return
    setAdding(true)
    setError(null)
    try {
      const created = await addPoamItem(poam.id, {
        practice_id: addForm.practice_id || undefined,
        milestone: addForm.milestone || undefined,
        scheduled_completion: addForm.scheduled_completion || undefined,
        resources_required: addForm.resources_required || undefined,
        risk_accepted: addForm.risk_accepted,
      })
      setPoam({ ...poam, items: [...poam.items, created] })
      setShowAddForm(false)
      setAddForm({ practice_id: '', milestone: '', scheduled_completion: '', resources_required: '', risk_accepted: false })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Add failed')
    } finally {
      setAdding(false)
    }
  }

  async function handleRemoveItem(itemId: string) {
    if (!poam) return
    try {
      await removePoamItem(poam.id, itemId)
      setPoam({ ...poam, items: poam.items.filter((i) => i.id !== itemId) })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Remove failed')
    }
  }

  async function handleActivate() {
    if (!poam) return
    try {
      const updated = await activatePoam(poam.id)
      setPoam({ ...poam, ...updated })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Activate failed')
    }
  }

  async function handleComplete() {
    if (!poam) return
    try {
      const updated = await completePoam(poam.id)
      setPoam({ ...poam, ...updated })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Complete failed')
    }
  }

  async function handleTitleSave() {
    if (!poam || !titleValue.trim()) return
    try {
      const updated = await updatePoam(poam.id, { title: titleValue.trim() })
      setPoam({ ...poam, ...updated })
      setEditingTitle(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <span className="loading loading-spinner loading-lg" />
      </div>
    )
  }

  if (error && !poam) {
    return (
      <div className="p-6">
        <div className="alert alert-error"><span>{error}</span></div>
      </div>
    )
  }

  if (!poam) return null

  const isCompleted = poam.status === 'completed'
  const overdueCount = poam.items.filter(isOverdue).length
  const completedCount = poam.items.filter((i) => i.status === 'completed').length
  const progress = poam.items.length > 0 ? Math.round((completedCount / poam.items.length) * 100) : 0

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link to="/poams" className="btn btn-ghost btn-xs">&larr; POA&Ms</Link>
            {editingTitle ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  className="input input-bordered input-sm"
                  value={titleValue}
                  onChange={(e) => setTitleValue(e.target.value)}
                  autoFocus
                  onKeyDown={(e) => { if (e.key === 'Enter') handleTitleSave(); if (e.key === 'Escape') setEditingTitle(false) }}
                />
                <button className="btn btn-primary btn-xs" onClick={handleTitleSave}>Save</button>
                <button className="btn btn-ghost btn-xs" onClick={() => setEditingTitle(false)}>Cancel</button>
              </div>
            ) : (
              <h1
                className={`text-2xl font-bold ${canManage && !isCompleted ? 'cursor-pointer hover:text-primary' : ''}`}
                onClick={() => {
                  if (canManage && !isCompleted) {
                    setTitleValue(poam.title)
                    setEditingTitle(true)
                  }
                }}
              >
                {poam.title}
              </h1>
            )}
            <span className={`badge badge-sm ${STATUS_BADGE[poam.status as POAMStatus]}`}>
              {poam.status}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-base-content/60">
            <span>{poam.items.length} item{poam.items.length !== 1 ? 's' : ''}</span>
            <span>{completedCount} completed</span>
            {overdueCount > 0 && (
              <span className="text-error font-medium">{overdueCount} overdue</span>
            )}
            {poam.assessment_id && (
              <Link to={`/assessments/${poam.assessment_id}`} className="link link-primary text-sm">
                View Assessment
              </Link>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to={`/poams/${poam.id}`} className="btn btn-ghost btn-sm">
            Kanban View
          </Link>
          <button className="btn btn-outline btn-sm" onClick={() => exportCsv(poam)}>
            Export CSV
          </button>
          {canManage && poam.status === 'draft' && (
            <button className="btn btn-info btn-sm" onClick={handleActivate}>Activate</button>
          )}
          {canManage && poam.status === 'active' && (
            <button className="btn btn-success btn-sm" onClick={handleComplete}>Complete</button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-base-content/60">Progress</span>
          <span className="font-medium">{progress}%</span>
        </div>
        <progress className="progress progress-success w-full" value={progress} max={100} />
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
          <button className="btn btn-ghost btn-xs ml-2" onClick={() => setError(null)}>dismiss</button>
        </div>
      )}

      {/* Add Item Button */}
      {canManage && !isCompleted && (
        <div className="flex justify-end mb-4">
          <button className="btn btn-primary btn-sm" onClick={() => setShowAddForm(true)}>
            + Add Item
          </button>
        </div>
      )}

      {/* Add Item Form */}
      {showAddForm && (
        <div className="card bg-base-100 shadow mb-6">
          <div className="card-body">
            <h2 className="card-title text-lg">Add Item</h2>
            <form onSubmit={handleAddItem} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="form-control">
                  <label className="label"><span className="label-text">Milestone</span></label>
                  <input
                    type="text"
                    className="input input-bordered input-sm"
                    value={addForm.milestone}
                    onChange={(e) => setAddForm({ ...addForm, milestone: e.target.value })}
                    maxLength={256}
                    placeholder="e.g. Deploy MFA solution"
                  />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Practice ID</span></label>
                  <input
                    type="text"
                    className="input input-bordered input-sm"
                    value={addForm.practice_id}
                    onChange={(e) => setAddForm({ ...addForm, practice_id: e.target.value })}
                    maxLength={32}
                    placeholder="e.g. AC.L2-3.1.3"
                  />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Scheduled Completion</span></label>
                  <input
                    type="date"
                    className="input input-bordered input-sm"
                    value={addForm.scheduled_completion}
                    onChange={(e) => setAddForm({ ...addForm, scheduled_completion: e.target.value })}
                  />
                </div>
                <div className="form-control">
                  <label className="label"><span className="label-text">Resources Required</span></label>
                  <input
                    type="text"
                    className="input input-bordered input-sm"
                    value={addForm.resources_required}
                    onChange={(e) => setAddForm({ ...addForm, resources_required: e.target.value })}
                    placeholder="e.g. IT security team"
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="checkbox checkbox-sm checkbox-warning"
                  checked={addForm.risk_accepted}
                  onChange={(e) => setAddForm({ ...addForm, risk_accepted: e.target.checked })}
                />
                <span className="label-text text-sm">Risk Accepted</span>
              </label>
              <div className="flex gap-2 justify-end">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowAddForm(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm" disabled={adding}>
                  {adding ? 'Adding...' : 'Add Item'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Items Table */}
      {poam.items.length === 0 ? (
        <div className="text-center py-12 text-base-content/50">
          <p className="text-lg mb-2">No items yet</p>
          <p className="text-sm">Add items manually or generate from assessment findings.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full">
            <thead>
              <tr>
                <th>Milestone</th>
                <th>Practice</th>
                <th>Status</th>
                <th>Due Date</th>
                <th>Completed</th>
                <th>Resources</th>
                <th>Risk</th>
                {canManage && !isCompleted && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {poam.items.map((item) => (
                editingItemId === item.id ? (
                  <tr key={item.id} className="bg-base-200">
                    <td colSpan={canManage && !isCompleted ? 8 : 7}>
                      <form onSubmit={handleSaveItem} className="space-y-3 py-2">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="form-control">
                            <label className="label"><span className="label-text text-xs">Milestone</span></label>
                            <input
                              type="text"
                              className="input input-bordered input-sm"
                              value={editForm.milestone}
                              onChange={(e) => setEditForm({ ...editForm, milestone: e.target.value })}
                              maxLength={256}
                            />
                          </div>
                          <div className="form-control">
                            <label className="label"><span className="label-text text-xs">Status</span></label>
                            <select
                              className="select select-bordered select-sm"
                              value={editForm.status}
                              onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                            >
                              <option value="open">Open</option>
                              <option value="in_progress">In Progress</option>
                              <option value="completed">Completed</option>
                            </select>
                          </div>
                          <div className="form-control">
                            <label className="label"><span className="label-text text-xs">Scheduled Completion</span></label>
                            <input
                              type="date"
                              className="input input-bordered input-sm"
                              value={editForm.scheduled_completion}
                              onChange={(e) => setEditForm({ ...editForm, scheduled_completion: e.target.value })}
                            />
                          </div>
                          <div className="form-control">
                            <label className="label"><span className="label-text text-xs">Resources</span></label>
                            <input
                              type="text"
                              className="input input-bordered input-sm"
                              value={editForm.resources_required}
                              onChange={(e) => setEditForm({ ...editForm, resources_required: e.target.value })}
                            />
                          </div>
                          <label className="flex items-center gap-2 cursor-pointer self-end pb-2">
                            <input
                              type="checkbox"
                              className="checkbox checkbox-sm checkbox-warning"
                              checked={editForm.risk_accepted}
                              onChange={(e) => setEditForm({ ...editForm, risk_accepted: e.target.checked })}
                            />
                            <span className="text-sm">Risk Accepted</span>
                          </label>
                        </div>
                        <div className="flex gap-2 justify-end">
                          <button type="button" className="btn btn-ghost btn-xs" onClick={() => setEditingItemId(null)}>Cancel</button>
                          <button type="submit" className="btn btn-primary btn-xs" disabled={saving}>
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                        </div>
                      </form>
                    </td>
                  </tr>
                ) : (
                  <tr key={item.id} className={isOverdue(item) ? 'bg-error/5' : ''}>
                    <td>
                      <div className="font-medium">{item.milestone || 'Untitled'}</div>
                      {item.finding_id && (
                        <div className="text-xs text-base-content/40">Finding: {item.finding_id.slice(0, 8)}</div>
                      )}
                    </td>
                    <td className="text-sm text-base-content/60">{item.practice_id || '\u2014'}</td>
                    <td>
                      <span className={`badge badge-sm ${ITEM_STATUS_BADGE[item.status]}`}>
                        {ITEM_STATUS_LABEL[item.status]}
                      </span>
                    </td>
                    <td>
                      <span className={`text-sm ${isOverdue(item) ? 'text-error font-medium' : 'text-base-content/60'}`}>
                        {item.scheduled_completion ? formatDate(item.scheduled_completion) : '\u2014'}
                      </span>
                      {isOverdue(item) && (
                        <div className="text-xs text-error">Overdue</div>
                      )}
                    </td>
                    <td className="text-sm text-base-content/60">
                      {item.actual_completion ? formatDate(item.actual_completion) : '\u2014'}
                    </td>
                    <td className="text-sm text-base-content/60 max-w-[200px] truncate">
                      {item.resources_required || '\u2014'}
                    </td>
                    <td>
                      {item.risk_accepted ? (
                        <span className="badge badge-xs badge-warning">Yes</span>
                      ) : (
                        <span className="text-sm text-base-content/40">No</span>
                      )}
                    </td>
                    {canManage && !isCompleted && (
                      <td>
                        <div className="flex gap-1">
                          <button className="btn btn-ghost btn-xs" onClick={() => openEditItem(item)}>Edit</button>
                          <button className="btn btn-ghost btn-xs text-error" onClick={() => handleRemoveItem(item.id)}>Remove</button>
                        </div>
                      </td>
                    )}
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
