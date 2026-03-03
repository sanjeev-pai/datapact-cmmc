import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/services/api'
import { getContracts } from '@/services/datapact'
import type { Contract } from '@/types/datapact'

interface OrgSettings {
  datapact_api_url: string | null
  datapact_api_key: string | null
}

export default function DataPactSettingsPage() {
  const { user } = useAuth()
  const orgId = user?.org_id

  const [apiUrl, setApiUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [contracts, setContracts] = useState<Contract[]>([])

  // Load org settings
  useEffect(() => {
    if (!orgId) {
      setLoading(false)
      return
    }
    api
      .get<{ datapact_api_url: string | null; datapact_api_key: string | null }>(
        `/organizations/${orgId}`,
      )
      .then((org: OrgSettings) => {
        setApiUrl(org.datapact_api_url || '')
        setApiKey(org.datapact_api_key || '')
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [orgId])

  async function handleSave() {
    if (!orgId) return
    setSaving(true)
    setSaveMsg(null)
    try {
      await api.patch(`/organizations/${orgId}`, {
        datapact_api_url: apiUrl || null,
        datapact_api_key: apiKey || null,
      })
      setSaveMsg('Settings saved')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Save failed'
      setSaveMsg(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleTestConnection() {
    setTesting(true)
    setTestResult(null)
    setContracts([])
    try {
      const data = await getContracts()
      setContracts(data.items || [])
      setTestResult({
        ok: true,
        message: `Connected — ${data.total ?? data.items?.length ?? 0} contract(s) found`,
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Connection failed'
      setTestResult({ ok: false, message: msg })
    } finally {
      setTesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <span className="loading loading-spinner loading-lg" />
      </div>
    )
  }

  if (!orgId) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">DataPact Settings</h1>
        <div className="alert alert-warning">
          You must belong to an organization to configure DataPact settings.
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">DataPact Settings</h1>
        <p className="text-base-content/60 text-sm mt-1">
          Configure your organization's DataPact integration
        </p>
      </div>

      {/* Settings form */}
      <div className="card bg-base-200 p-6 mb-6">
        <div className="form-control mb-4">
          <label className="label" htmlFor="dp-api-url">
            <span className="label-text font-medium">DataPact API URL</span>
          </label>
          <input
            id="dp-api-url"
            type="url"
            className="input input-bordered w-full"
            placeholder="http://localhost:8180"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
          />
        </div>

        <div className="form-control mb-4">
          <label className="label" htmlFor="dp-api-key">
            <span className="label-text font-medium">API Key</span>
          </label>
          <input
            id="dp-api-key"
            type="password"
            className="input input-bordered w-full"
            placeholder="Enter API key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <button
            className="btn btn-primary btn-sm"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={handleTestConnection}
            disabled={testing}
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        </div>

        {saveMsg && (
          <div className={`alert mt-3 ${saveMsg === 'Settings saved' ? 'alert-success' : 'alert-error'}`}>
            <span>{saveMsg}</span>
          </div>
        )}

        {testResult && (
          <div className={`alert mt-3 ${testResult.ok ? 'alert-success' : 'alert-error'}`}>
            <span>{testResult.message}</span>
          </div>
        )}
      </div>

      {/* Contract preview */}
      {contracts.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Contracts Preview</h2>
          <div className="overflow-x-auto">
            <table className="table table-zebra w-full">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>ID</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div className="font-medium">{c.title}</div>
                      {c.description && (
                        <div className="text-xs text-base-content/50 truncate max-w-xs">
                          {c.description}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className="badge badge-sm badge-ghost">
                        {c.status || 'unknown'}
                      </span>
                    </td>
                    <td className="text-sm text-base-content/60 font-mono">
                      {c.id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
