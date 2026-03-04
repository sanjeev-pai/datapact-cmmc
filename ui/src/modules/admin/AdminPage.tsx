import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import {
  listOrganizations,
  createOrganization,
  updateOrganization,
  deleteOrganization,
  type Organization,
} from '@/services/organizations'
import {
  listUsers,
  updateUser,
  deactivateUser,
  type AdminUser,
} from '@/services/users'

const ROLE_OPTIONS = [
  'system_admin',
  'org_admin',
  'compliance_officer',
  'assessor',
  'c3pao_lead',
  'viewer',
]

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014'
  return new Date(dateStr).toLocaleDateString()
}

export default function AdminPage() {
  const { user, hasRole } = useAuth()
  const isSystemAdmin = hasRole('system_admin')
  const isOrgAdmin = hasRole('org_admin')

  const [tab, setTab] = useState<'orgs' | 'users'>('orgs')
  const [error, setError] = useState<string | null>(null)

  // --- Organizations ---
  const [orgs, setOrgs] = useState<Organization[]>([])
  const [orgsLoading, setOrgsLoading] = useState(true)
  const [showOrgForm, setShowOrgForm] = useState(false)
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null)
  const [orgForm, setOrgForm] = useState({ name: '', cage_code: '', duns_number: '', target_level: '' })
  const [orgSaving, setOrgSaving] = useState(false)

  // --- Users ---
  const [users, setUsers] = useState<AdminUser[]>([])
  const [usersLoading, setUsersLoading] = useState(true)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [userForm, setUserForm] = useState({ username: '', email: '', org_id: '', roles: [] as string[], is_active: true })
  const [userSaving, setUserSaving] = useState(false)

  // Load orgs
  useEffect(() => {
    setOrgsLoading(true)
    listOrganizations()
      .then(setOrgs)
      .catch((err) => setError(err.message || 'Failed to load organizations'))
      .finally(() => setOrgsLoading(false))
  }, [])

  // Load users
  useEffect(() => {
    setUsersLoading(true)
    listUsers()
      .then(setUsers)
      .catch((err) => setError(err.message || 'Failed to load users'))
      .finally(() => setUsersLoading(false))
  }, [])

  // --- Org handlers ---
  function openCreateOrg() {
    setEditingOrg(null)
    setOrgForm({ name: '', cage_code: '', duns_number: '', target_level: '' })
    setShowOrgForm(true)
  }

  function openEditOrg(org: Organization) {
    setEditingOrg(org)
    setOrgForm({
      name: org.name,
      cage_code: org.cage_code || '',
      duns_number: org.duns_number || '',
      target_level: org.target_level?.toString() || '',
    })
    setShowOrgForm(true)
  }

  async function handleOrgSubmit(e: React.FormEvent) {
    e.preventDefault()
    setOrgSaving(true)
    setError(null)
    try {
      const payload = {
        name: orgForm.name,
        cage_code: orgForm.cage_code || undefined,
        duns_number: orgForm.duns_number || undefined,
        target_level: orgForm.target_level ? parseInt(orgForm.target_level) : undefined,
      }
      if (editingOrg) {
        const updated = await updateOrganization(editingOrg.id, payload)
        setOrgs((prev) => prev.map((o) => (o.id === updated.id ? updated : o)))
      } else {
        const created = await createOrganization(payload)
        setOrgs((prev) => [...prev, created])
      }
      setShowOrgForm(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setOrgSaving(false)
    }
  }

  async function handleDeleteOrg(id: string) {
    try {
      await deleteOrganization(id)
      setOrgs((prev) => prev.filter((o) => o.id !== id))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  // --- User handlers ---
  function openEditUser(u: AdminUser) {
    setEditingUser(u)
    setUserForm({
      username: u.username,
      email: u.email,
      org_id: u.org_id || '',
      roles: [...u.roles],
      is_active: u.is_active,
    })
  }

  async function handleUserSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!editingUser) return
    setUserSaving(true)
    setError(null)
    try {
      const payload: Record<string, unknown> = {}
      if (userForm.username !== editingUser.username) payload.username = userForm.username
      if (userForm.email !== editingUser.email) payload.email = userForm.email
      if (userForm.org_id !== (editingUser.org_id || '')) payload.org_id = userForm.org_id || null
      if (userForm.is_active !== editingUser.is_active) payload.is_active = userForm.is_active
      if (JSON.stringify(userForm.roles.sort()) !== JSON.stringify([...editingUser.roles].sort())) {
        payload.roles = userForm.roles
      }
      const updated = await updateUser(editingUser.id, payload)
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)))
      setEditingUser(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setUserSaving(false)
    }
  }

  async function handleDeactivateUser(id: string) {
    try {
      await deactivateUser(id)
      setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, is_active: false } : u)))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Deactivate failed')
    }
  }

  function toggleRole(role: string) {
    setUserForm((prev) => ({
      ...prev,
      roles: prev.roles.includes(role)
        ? prev.roles.filter((r) => r !== role)
        : [...prev.roles, role],
    }))
  }

  function getOrgName(orgId: string | null): string {
    if (!orgId) return '\u2014'
    const org = orgs.find((o) => o.id === orgId)
    return org ? org.name : orgId.slice(0, 8)
  }

  if (!isSystemAdmin && !isOrgAdmin) {
    return (
      <div className="p-6">
        <div className="alert alert-warning">
          <span>You do not have admin permissions.</span>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-1">Admin</h1>
      <p className="text-base-content/60 text-sm mb-6">
        Manage organizations and users
      </p>

      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
          <button className="btn btn-ghost btn-xs ml-2" onClick={() => setError(null)}>dismiss</button>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs tabs-bordered mb-6">
        <button
          className={`tab ${tab === 'orgs' ? 'tab-active' : ''}`}
          onClick={() => setTab('orgs')}
        >
          Organizations
        </button>
        <button
          className={`tab ${tab === 'users' ? 'tab-active' : ''}`}
          onClick={() => setTab('users')}
        >
          Users
        </button>
      </div>

      {/* ===== Organizations Tab ===== */}
      {tab === 'orgs' && (
        <>
          {isSystemAdmin && (
            <div className="flex justify-end mb-4">
              <button className="btn btn-primary btn-sm" onClick={openCreateOrg}>
                + New Organization
              </button>
            </div>
          )}

          {showOrgForm && (
            <div className="card bg-base-100 shadow mb-6">
              <div className="card-body">
                <h2 className="card-title text-lg">
                  {editingOrg ? 'Edit Organization' : 'New Organization'}
                </h2>
                <form onSubmit={handleOrgSubmit} className="space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="form-control">
                      <label className="label"><span className="label-text">Name *</span></label>
                      <input
                        type="text"
                        className="input input-bordered input-sm"
                        value={orgForm.name}
                        onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value })}
                        required
                        maxLength={256}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label"><span className="label-text">CAGE Code</span></label>
                      <input
                        type="text"
                        className="input input-bordered input-sm"
                        value={orgForm.cage_code}
                        onChange={(e) => setOrgForm({ ...orgForm, cage_code: e.target.value })}
                        maxLength={8}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label"><span className="label-text">DUNS Number</span></label>
                      <input
                        type="text"
                        className="input input-bordered input-sm"
                        value={orgForm.duns_number}
                        onChange={(e) => setOrgForm({ ...orgForm, duns_number: e.target.value })}
                        maxLength={16}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label"><span className="label-text">Target Level</span></label>
                      <select
                        className="select select-bordered select-sm"
                        value={orgForm.target_level}
                        onChange={(e) => setOrgForm({ ...orgForm, target_level: e.target.value })}
                      >
                        <option value="">None</option>
                        <option value="1">Level 1</option>
                        <option value="2">Level 2</option>
                        <option value="3">Level 3</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowOrgForm(false)}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary btn-sm" disabled={orgSaving}>
                      {orgSaving ? 'Saving...' : editingOrg ? 'Update' : 'Create'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {orgsLoading ? (
            <div className="flex justify-center py-12">
              <span className="loading loading-spinner loading-lg" />
            </div>
          ) : orgs.length === 0 ? (
            <div className="text-center py-12 text-base-content/50">
              <p className="text-lg">No organizations found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table table-zebra w-full">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>CAGE Code</th>
                    <th>DUNS</th>
                    <th>Target Level</th>
                    <th>Created</th>
                    {isSystemAdmin && <th>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {orgs.map((org) => (
                    <tr key={org.id}>
                      <td className="font-medium">{org.name}</td>
                      <td className="text-sm text-base-content/60">{org.cage_code || '\u2014'}</td>
                      <td className="text-sm text-base-content/60">{org.duns_number || '\u2014'}</td>
                      <td>
                        {org.target_level ? (
                          <span className="badge badge-sm badge-info">L{org.target_level}</span>
                        ) : '\u2014'}
                      </td>
                      <td className="text-sm text-base-content/60">{formatDate(org.created_at)}</td>
                      {isSystemAdmin && (
                        <td>
                          <div className="flex gap-1">
                            <button className="btn btn-ghost btn-xs" onClick={() => openEditOrg(org)}>
                              Edit
                            </button>
                            <button
                              className="btn btn-ghost btn-xs text-error"
                              onClick={() => handleDeleteOrg(org.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ===== Users Tab ===== */}
      {tab === 'users' && (
        <>
          {editingUser && (
            <div className="card bg-base-100 shadow mb-6">
              <div className="card-body">
                <h2 className="card-title text-lg">Edit User: {editingUser.username}</h2>
                <form onSubmit={handleUserSubmit} className="space-y-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="form-control">
                      <label className="label"><span className="label-text">Username</span></label>
                      <input
                        type="text"
                        className="input input-bordered input-sm"
                        value={userForm.username}
                        onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                        minLength={3}
                        maxLength={128}
                      />
                    </div>
                    <div className="form-control">
                      <label className="label"><span className="label-text">Email</span></label>
                      <input
                        type="email"
                        className="input input-bordered input-sm"
                        value={userForm.email}
                        onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                      />
                    </div>
                    {isSystemAdmin && (
                      <div className="form-control">
                        <label className="label"><span className="label-text">Organization</span></label>
                        <select
                          className="select select-bordered select-sm"
                          value={userForm.org_id}
                          onChange={(e) => setUserForm({ ...userForm, org_id: e.target.value })}
                        >
                          <option value="">None</option>
                          {orgs.map((o) => (
                            <option key={o.id} value={o.id}>{o.name}</option>
                          ))}
                        </select>
                      </div>
                    )}
                    <div className="form-control">
                      <label className="label"><span className="label-text">Active</span></label>
                      <input
                        type="checkbox"
                        className="toggle toggle-primary"
                        checked={userForm.is_active}
                        onChange={(e) => setUserForm({ ...userForm, is_active: e.target.checked })}
                      />
                    </div>
                  </div>
                  <div className="form-control">
                    <label className="label"><span className="label-text">Roles</span></label>
                    <div className="flex flex-wrap gap-2">
                      {ROLE_OPTIONS.map((role) => (
                        <label key={role} className="flex items-center gap-1 cursor-pointer">
                          <input
                            type="checkbox"
                            className="checkbox checkbox-sm checkbox-primary"
                            checked={userForm.roles.includes(role)}
                            onChange={() => toggleRole(role)}
                            disabled={!isSystemAdmin && role === 'system_admin'}
                          />
                          <span className="text-sm">{role}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEditingUser(null)}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary btn-sm" disabled={userSaving}>
                      {userSaving ? 'Saving...' : 'Update'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {usersLoading ? (
            <div className="flex justify-center py-12">
              <span className="loading loading-spinner loading-lg" />
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12 text-base-content/50">
              <p className="text-lg">No users found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="table table-zebra w-full">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Organization</th>
                    <th>Roles</th>
                    <th>Active</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className="font-medium">{u.username}</td>
                      <td className="text-sm text-base-content/60">{u.email}</td>
                      <td className="text-sm text-base-content/60">{getOrgName(u.org_id)}</td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          {u.roles.map((r) => (
                            <span key={r} className="badge badge-xs badge-ghost">{r}</span>
                          ))}
                        </div>
                      </td>
                      <td>
                        {u.is_active ? (
                          <span className="badge badge-xs badge-success">active</span>
                        ) : (
                          <span className="badge badge-xs badge-error">inactive</span>
                        )}
                      </td>
                      <td className="text-sm text-base-content/60">{formatDate(u.created_at)}</td>
                      <td>
                        <div className="flex gap-1">
                          <button className="btn btn-ghost btn-xs" onClick={() => openEditUser(u)}>
                            Edit
                          </button>
                          {u.is_active && u.id !== user?.id && (
                            <button
                              className="btn btn-ghost btn-xs text-error"
                              onClick={() => handleDeactivateUser(u.id)}
                            >
                              Deactivate
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
