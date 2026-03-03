import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { getMappings, createMapping, deleteMapping, getContracts, suggestMappings } from '@/services/datapact'
import { getPractices } from '@/services/cmmc'
import type { Mapping, Contract, MappingSuggestion } from '@/types/datapact'
import type { CMMCPractice } from '@/types/cmmc'
import DataPactNav from './DataPactNav'

export default function DataPactMappingsPage() {
  const { user, hasRole } = useAuth()
  const isAdmin = hasRole('system_admin')
  const orgId = user?.org_id

  const [mappings, setMappings] = useState<Mapping[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [practices, setPractices] = useState<CMMCPractice[]>([])
  const [suggestions, setSuggestions] = useState<MappingSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Add form state
  const [selectedPractice, setSelectedPractice] = useState('')
  const [selectedContract, setSelectedContract] = useState('')
  const [adding, setAdding] = useState(false)
  const [suggesting, setSuggesting] = useState(false)

  // Filter state
  const [filterDomain, setFilterDomain] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [mappingsData, contractsData, practicesData] = await Promise.all([
        getMappings(),
        getContracts().catch(() => ({ items: [], total: 0 })),
        getPractices(),
      ])
      setMappings(mappingsData.items)
      setContracts(contractsData.items)
      setPractices(practicesData)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load data'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!orgId && !isAdmin) {
      setLoading(false)
      return
    }
    loadData()
  }, [orgId, isAdmin, loadData])

  async function handleAdd() {
    if (!selectedPractice || !selectedContract) return
    setAdding(true)
    setError(null)
    try {
      const contract = contracts.find((c) => c.id === selectedContract)
      await createMapping({
        practice_id: selectedPractice,
        datapact_contract_id: selectedContract,
        datapact_contract_name: contract?.title,
      })
      setSelectedPractice('')
      setSelectedContract('')
      await loadData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create mapping'
      setError(msg)
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(id: string) {
    setError(null)
    try {
      await deleteMapping(id)
      setMappings((prev) => prev.filter((m) => m.id !== id))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete mapping'
      setError(msg)
    }
  }

  async function handleSuggest() {
    setSuggesting(true)
    setSuggestions([])
    setError(null)
    try {
      const data = await suggestMappings()
      setSuggestions(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to get suggestions'
      setError(msg)
    } finally {
      setSuggesting(false)
    }
  }

  async function handleAcceptSuggestion(suggestion: MappingSuggestion) {
    setError(null)
    try {
      await createMapping({
        practice_id: suggestion.practice_id,
        datapact_contract_id: suggestion.contract_id,
        datapact_contract_name: suggestion.contract_name || undefined,
      })
      setSuggestions((prev) =>
        prev.filter(
          (s) => !(s.practice_id === suggestion.practice_id && s.contract_id === suggestion.contract_id),
        ),
      )
      await loadData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to accept suggestion'
      setError(msg)
    }
  }

  // Group practices by domain for display
  const domains = [...new Set(practices.map((p) => p.domain_ref))].sort()

  const filteredMappings = filterDomain
    ? mappings.filter((m) => m.practice_id.startsWith(filterDomain + '.'))
    : mappings

  // Helper to look up practice title
  function practiceName(practiceId: string): string {
    const p = practices.find((pr) => pr.practice_id === practiceId)
    return p ? `${practiceId} — ${p.title}` : practiceId
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <span className="loading loading-spinner loading-lg" />
      </div>
    )
  }

  if (!orgId && !isAdmin) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-4">Practice Mappings</h1>
        <div className="alert alert-warning">
          You must belong to an organization to manage practice mappings.
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">DataPact Integration</h1>
        <p className="text-base-content/60 text-sm mt-1">
          Map CMMC practices to DataPact contracts
        </p>
      </div>
      <DataPactNav />

      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
        </div>
      )}

      {/* Add mapping form */}
      <div className="card bg-base-200 p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Add Mapping</h2>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="form-control flex-1 min-w-[200px]">
            <label className="label" htmlFor="practice-select">
              <span className="label-text text-sm">Practice</span>
            </label>
            <select
              id="practice-select"
              className="select select-bordered select-sm w-full"
              value={selectedPractice}
              onChange={(e) => setSelectedPractice(e.target.value)}
            >
              <option value="">Select practice...</option>
              {domains.map((domain) => (
                <optgroup key={domain} label={domain}>
                  {practices
                    .filter((p) => p.domain_ref === domain)
                    .map((p) => (
                      <option key={p.practice_id} value={p.practice_id}>
                        {p.practice_id} — {p.title}
                      </option>
                    ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="form-control flex-1 min-w-[200px]">
            <label className="label" htmlFor="contract-select">
              <span className="label-text text-sm">Contract</span>
            </label>
            <select
              id="contract-select"
              className="select select-bordered select-sm w-full"
              value={selectedContract}
              onChange={(e) => setSelectedContract(e.target.value)}
            >
              <option value="">Select contract...</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} ({c.id})
                </option>
              ))}
            </select>
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleAdd}
            disabled={adding || !selectedPractice || !selectedContract}
          >
            {adding ? 'Adding...' : 'Add Mapping'}
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={handleSuggest}
            disabled={suggesting}
          >
            {suggesting ? 'Suggesting...' : 'Auto-Suggest'}
          </button>
        </div>
        {contracts.length === 0 && (
          <p className="text-xs text-base-content/50 mt-2">
            No contracts available. Configure DataPact connection in Settings first.
          </p>
        )}
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="card bg-info/10 border border-info/30 p-4 mb-6">
          <h2 className="text-lg font-semibold mb-3">
            Suggested Mappings ({suggestions.length})
          </h2>
          <div className="overflow-x-auto">
            <table className="table table-sm w-full">
              <thead>
                <tr>
                  <th>Practice</th>
                  <th>Contract</th>
                  <th>Reason</th>
                  <th className="w-20">Action</th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((s) => (
                  <tr key={`${s.practice_id}-${s.contract_id}`}>
                    <td className="font-mono text-sm">{s.practice_id}</td>
                    <td>{s.contract_name || s.contract_id}</td>
                    <td className="text-sm text-base-content/60">{s.reason}</td>
                    <td>
                      <button
                        className="btn btn-success btn-xs"
                        onClick={() => handleAcceptSuggestion(s)}
                      >
                        Accept
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Filter + count */}
      <div className="flex items-center gap-3 mb-3">
        <select
          className="select select-bordered select-sm"
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          aria-label="Filter by domain"
        >
          <option value="">All domains</option>
          {domains.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <span className="text-sm text-base-content/60">
          {filteredMappings.length} mapping{filteredMappings.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Mappings table */}
      {filteredMappings.length === 0 ? (
        <div className="text-center py-8 text-base-content/50">
          No mappings found. Add a mapping above or use Auto-Suggest.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full">
            <thead>
              <tr>
                <th>Practice</th>
                <th>Contract</th>
                <th>Created</th>
                <th className="w-20">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredMappings.map((m) => (
                <tr key={m.id}>
                  <td>
                    <div className="font-medium text-sm">{practiceName(m.practice_id)}</div>
                  </td>
                  <td>
                    <div className="font-medium">{m.datapact_contract_name || m.datapact_contract_id}</div>
                    {m.datapact_contract_name && (
                      <div className="text-xs text-base-content/50 font-mono">{m.datapact_contract_id}</div>
                    )}
                  </td>
                  <td className="text-sm text-base-content/60">
                    {new Date(m.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <button
                      className="btn btn-ghost btn-xs text-error"
                      onClick={() => handleDelete(m.id)}
                      aria-label={`Delete mapping ${m.practice_id}`}
                    >
                      Delete
                    </button>
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
