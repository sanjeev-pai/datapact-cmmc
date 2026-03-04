import { useEffect, useState, type DragEvent } from 'react'
import { useParams, Link } from 'react-router-dom'
import type { POAMDetail, POAMItem, POAMItemStatus } from '@/types/poam'
import { getPoam, updatePoamItem } from '@/services/poam'
import { useAuth } from '@/hooks/useAuth'

const COLUMNS: { status: POAMItemStatus; label: string; color: string }[] = [
  { status: 'open', label: 'Open', color: 'border-base-300' },
  { status: 'in_progress', label: 'In Progress', color: 'border-info' },
  { status: 'completed', label: 'Completed', color: 'border-success' },
]

const MANAGE_ROLES = ['system_admin', 'org_admin', 'compliance_officer', 'assessor', 'c3pao_lead']

const VALID_TRANSITIONS: Record<POAMItemStatus, POAMItemStatus[]> = {
  open: ['in_progress'],
  in_progress: ['completed'],
  completed: [],
}

function isOverdue(item: POAMItem): boolean {
  if (item.status === 'completed' || !item.scheduled_completion) return false
  return item.scheduled_completion < new Date().toISOString().slice(0, 10)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  return new Date(dateStr).toLocaleDateString()
}

export default function POAMKanbanPage() {
  const { id } = useParams<{ id: string }>()
  const { hasRole } = useAuth()
  const canManage = hasRole(...MANAGE_ROLES)

  const [poam, setPoam] = useState<POAMDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dragItemId, setDragItemId] = useState<string | null>(null)
  const [dropTarget, setDropTarget] = useState<POAMItemStatus | null>(null)

  // Detail panel
  const [selectedItem, setSelectedItem] = useState<POAMItem | null>(null)
  const [editForm, setEditForm] = useState({
    milestone: '',
    scheduled_completion: '',
    resources_required: '',
    risk_accepted: false,
  })
  const [saving, setSaving] = useState(false)

  // Filters
  const [assigneeFilter, setAssigneeFilter] = useState('')
  const [dueDateFilter, setDueDateFilter] = useState<'all' | 'overdue' | 'upcoming'>('all')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getPoam(id)
      .then(setPoam)
      .catch((err) => setError(err.message || 'Failed to load POA&M'))
      .finally(() => setLoading(false))
  }, [id])

  function getColumnItems(status: POAMItemStatus): POAMItem[] {
    if (!poam) return []
    let items = poam.items.filter((i) => i.status === status)

    if (dueDateFilter === 'overdue') {
      items = items.filter(isOverdue)
    } else if (dueDateFilter === 'upcoming') {
      const today = new Date().toISOString().slice(0, 10)
      const weekAhead = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)
      items = items.filter(
        (i) => i.scheduled_completion && i.scheduled_completion >= today && i.scheduled_completion <= weekAhead,
      )
    }

    if (assigneeFilter) {
      items = items.filter((i) => i.practice_id?.toLowerCase().includes(assigneeFilter.toLowerCase()))
    }

    return items
  }

  function canDrop(targetStatus: POAMItemStatus): boolean {
    if (!dragItemId || !poam) return false
    const item = poam.items.find((i) => i.id === dragItemId)
    if (!item) return false
    return VALID_TRANSITIONS[item.status].includes(targetStatus)
  }

  function handleDragStart(e: DragEvent, itemId: string) {
    setDragItemId(itemId)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', itemId)
  }

  function handleDragOver(e: DragEvent, status: POAMItemStatus) {
    if (canDrop(status)) {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      setDropTarget(status)
    }
  }

  function handleDragLeave() {
    setDropTarget(null)
  }

  async function handleDrop(e: DragEvent, targetStatus: POAMItemStatus) {
    e.preventDefault()
    setDropTarget(null)
    setDragItemId(null)

    const itemId = e.dataTransfer.getData('text/plain')
    if (!itemId || !poam || !id) return

    const item = poam.items.find((i) => i.id === itemId)
    if (!item || !VALID_TRANSITIONS[item.status].includes(targetStatus)) return

    try {
      const updated = await updatePoamItem(poam.id, itemId, { status: targetStatus })
      setPoam({
        ...poam,
        items: poam.items.map((i) => (i.id === updated.id ? updated : i)),
      })
      if (selectedItem?.id === updated.id) setSelectedItem(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Status update failed')
    }
  }

  async function handleStatusClick(item: POAMItem, targetStatus: POAMItemStatus) {
    if (!poam || !id) return
    try {
      const updated = await updatePoamItem(poam.id, item.id, { status: targetStatus })
      setPoam({
        ...poam,
        items: poam.items.map((i) => (i.id === updated.id ? updated : i)),
      })
      if (selectedItem?.id === updated.id) setSelectedItem(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Status update failed')
    }
  }

  function openDetail(item: POAMItem) {
    setSelectedItem(item)
    setEditForm({
      milestone: item.milestone || '',
      scheduled_completion: item.scheduled_completion || '',
      resources_required: item.resources_required || '',
      risk_accepted: item.risk_accepted,
    })
  }

  async function handleDetailSave(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedItem || !poam) return
    setSaving(true)
    setError(null)
    try {
      const updated = await updatePoamItem(poam.id, selectedItem.id, {
        milestone: editForm.milestone || undefined,
        scheduled_completion: editForm.scheduled_completion || null,
        resources_required: editForm.resources_required || null,
        risk_accepted: editForm.risk_accepted,
      })
      setPoam({
        ...poam,
        items: poam.items.map((i) => (i.id === updated.id ? updated : i)),
      })
      setSelectedItem(updated)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
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
        <div className="alert alert-error">
          <span>{error}</span>
        </div>
      </div>
    )
  }

  if (!poam) return null

  const isCompleted = poam.status === 'completed'

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link to="/poams" className="btn btn-ghost btn-xs">
              &larr; POA&Ms
            </Link>
            <h1 className="text-2xl font-bold">{poam.title}</h1>
            <span className={`badge badge-sm ${
              poam.status === 'draft' ? 'badge-ghost' :
              poam.status === 'active' ? 'badge-info' : 'badge-success'
            }`}>
              {poam.status}
            </span>
          </div>
          <p className="text-base-content/60 text-sm">
            {poam.items.length} item{poam.items.length !== 1 ? 's' : ''}
            {' \u00b7 '}
            {poam.items.filter(isOverdue).length} overdue
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
          <button className="btn btn-ghost btn-xs ml-2" onClick={() => setError(null)}>dismiss</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          className="input input-bordered input-sm w-48"
          placeholder="Filter by practice ID..."
          value={assigneeFilter}
          onChange={(e) => setAssigneeFilter(e.target.value)}
        />
        <select
          className="select select-bordered select-sm"
          value={dueDateFilter}
          onChange={(e) => setDueDateFilter(e.target.value as typeof dueDateFilter)}
          aria-label="Filter by due date"
        >
          <option value="all">All Items</option>
          <option value="overdue">Overdue Only</option>
          <option value="upcoming">Due This Week</option>
        </select>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 flex gap-4 overflow-x-auto min-h-0">
        {COLUMNS.map((col) => {
          const items = getColumnItems(col.status)
          const isDragTarget = dropTarget === col.status && canDrop(col.status)

          return (
            <div
              key={col.status}
              className={`flex flex-col w-80 min-w-[20rem] rounded-lg border-t-4 ${col.color} bg-base-100 ${
                isDragTarget ? 'ring-2 ring-primary ring-offset-2' : ''
              }`}
              onDragOver={(e) => handleDragOver(e, col.status)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, col.status)}
            >
              {/* Column header */}
              <div className="px-3 py-2 border-b border-base-200 flex items-center justify-between">
                <span className="font-medium text-sm">{col.label}</span>
                <span className="badge badge-sm badge-ghost">{items.length}</span>
              </div>

              {/* Cards */}
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {items.length === 0 && (
                  <div className="text-center text-base-content/30 text-xs py-8">
                    No items
                  </div>
                )}
                {items.map((item) => (
                  <div
                    key={item.id}
                    className={`card bg-base-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${
                      selectedItem?.id === item.id ? 'ring-2 ring-primary' : ''
                    } ${isOverdue(item) ? 'border-l-4 border-error' : ''}`}
                    draggable={canManage && !isCompleted}
                    onDragStart={(e) => handleDragStart(e, item.id)}
                    onDragEnd={() => { setDragItemId(null); setDropTarget(null) }}
                    onClick={() => openDetail(item)}
                  >
                    <div className="card-body p-3">
                      <div className="text-sm font-medium">
                        {item.milestone || 'Untitled item'}
                      </div>
                      {item.practice_id && (
                        <div className="text-xs text-base-content/50">{item.practice_id}</div>
                      )}
                      <div className="flex items-center justify-between mt-1">
                        <span className={`text-xs ${isOverdue(item) ? 'text-error font-medium' : 'text-base-content/50'}`}>
                          {item.scheduled_completion
                            ? (isOverdue(item) ? 'Overdue: ' : 'Due: ') + formatDate(item.scheduled_completion)
                            : 'No due date'}
                        </span>
                        {item.risk_accepted && (
                          <span className="badge badge-xs badge-warning">Risk</span>
                        )}
                      </div>

                      {/* Quick status transition buttons */}
                      {canManage && !isCompleted && VALID_TRANSITIONS[item.status].length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {VALID_TRANSITIONS[item.status].map((next) => (
                            <button
                              key={next}
                              className="btn btn-ghost btn-xs text-xs"
                              onClick={(e) => { e.stopPropagation(); handleStatusClick(item, next) }}
                            >
                              {next === 'in_progress' ? 'Start' : 'Complete'} &rarr;
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Detail Panel */}
      {selectedItem && (
        <div className="fixed inset-y-0 right-0 w-96 bg-base-100 shadow-xl border-l border-base-300 z-50 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-base-300">
            <h3 className="font-bold text-lg">Item Detail</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => setSelectedItem(null)}>&times;</button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-3">
              <div>
                <span className="text-xs text-base-content/50">Status</span>
                <div>
                  <span className={`badge badge-sm ${
                    selectedItem.status === 'open' ? 'badge-ghost' :
                    selectedItem.status === 'in_progress' ? 'badge-info' : 'badge-success'
                  }`}>
                    {selectedItem.status === 'in_progress' ? 'In Progress' :
                     selectedItem.status.charAt(0).toUpperCase() + selectedItem.status.slice(1)}
                  </span>
                  {isOverdue(selectedItem) && (
                    <span className="badge badge-sm badge-error ml-1">Overdue</span>
                  )}
                </div>
              </div>

              {selectedItem.practice_id && (
                <div>
                  <span className="text-xs text-base-content/50">Practice</span>
                  <div className="text-sm">{selectedItem.practice_id}</div>
                </div>
              )}

              {selectedItem.finding_id && (
                <div>
                  <span className="text-xs text-base-content/50">Finding ID</span>
                  <div className="text-sm font-mono">{selectedItem.finding_id.slice(0, 12)}</div>
                </div>
              )}

              <div>
                <span className="text-xs text-base-content/50">Created</span>
                <div className="text-sm">{formatDate(selectedItem.created_at)}</div>
              </div>

              {selectedItem.actual_completion && (
                <div>
                  <span className="text-xs text-base-content/50">Completed</span>
                  <div className="text-sm">{formatDate(selectedItem.actual_completion)}</div>
                </div>
              )}

              {canManage && !isCompleted && (
                <form onSubmit={handleDetailSave} className="space-y-3 pt-3 border-t border-base-200">
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
                    <label className="label"><span className="label-text text-xs">Scheduled Completion</span></label>
                    <input
                      type="date"
                      className="input input-bordered input-sm"
                      value={editForm.scheduled_completion}
                      onChange={(e) => setEditForm({ ...editForm, scheduled_completion: e.target.value })}
                    />
                  </div>
                  <div className="form-control">
                    <label className="label"><span className="label-text text-xs">Resources Required</span></label>
                    <textarea
                      className="textarea textarea-bordered textarea-sm"
                      rows={2}
                      value={editForm.resources_required}
                      onChange={(e) => setEditForm({ ...editForm, resources_required: e.target.value })}
                    />
                  </div>
                  <div className="form-control">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        className="checkbox checkbox-sm checkbox-warning"
                        checked={editForm.risk_accepted}
                        onChange={(e) => setEditForm({ ...editForm, risk_accepted: e.target.checked })}
                      />
                      <span className="label-text text-xs">Risk Accepted</span>
                    </label>
                  </div>
                  <button type="submit" className="btn btn-primary btn-sm w-full" disabled={saving}>
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
