import { useEffect, useState } from 'react'
import type { CMMCDomain, CMMCPractice } from '@/types/cmmc'
import { getDomains, getPractices, getPractice } from '@/services/cmmc'

const LEVEL_BADGES: Record<number, string> = {
  1: 'badge-success',
  2: 'badge-warning',
  3: 'badge-error',
}

const LEVEL_NAMES: Record<number, string> = {
  1: 'Level 1 — Foundational',
  2: 'Level 2 — Advanced',
  3: 'Level 3 — Expert',
}

export default function CMMCLibraryPage() {
  const [domains, setDomains] = useState<CMMCDomain[]>([])
  const [practices, setPractices] = useState<CMMCPractice[]>([])
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [selectedLevel, setSelectedLevel] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPractice, setSelectedPractice] = useState<CMMCPractice | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load domains on mount
  useEffect(() => {
    getDomains()
      .then(setDomains)
      .catch((e) => setError(e.message))
  }, [])

  // Load practices when filters change
  useEffect(() => {
    setLoading(true)
    setError(null)
    getPractices({
      domain: selectedDomain ?? undefined,
      level: selectedLevel ?? undefined,
      search: searchQuery || undefined,
    })
      .then((data) => {
        setPractices(data)
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }, [selectedDomain, selectedLevel, searchQuery])

  function handlePracticeClick(practiceId: string) {
    getPractice(practiceId)
      .then(setSelectedPractice)
      .catch((e) => setError(e.message))
  }

  // Group practices by domain for display
  const grouped = practices.reduce<Record<string, CMMCPractice[]>>((acc, p) => {
    const key = p.domain_ref
    if (!acc[key]) acc[key] = []
    acc[key].push(p)
    return acc
  }, {})

  const domainMap = Object.fromEntries(domains.map((d) => [d.domain_id, d]))

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">CMMC Practice Library</h1>
        <p className="text-base-content/60 mt-1">
          Browse CMMC 2.0 domains and practices across all maturity levels.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        {/* Search */}
        <input
          type="text"
          placeholder="Search practices..."
          className="input input-bordered input-sm w-64"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        {/* Level filter */}
        <div className="flex gap-1">
          <button
            className={`btn btn-sm ${selectedLevel === null ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setSelectedLevel(null)}
          >
            All Levels
          </button>
          {[1, 2, 3].map((lvl) => (
            <button
              key={lvl}
              className={`btn btn-sm ${selectedLevel === lvl ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setSelectedLevel(lvl)}
            >
              L{lvl}
            </button>
          ))}
        </div>

        {/* Domain filter */}
        <select
          className="select select-bordered select-sm"
          value={selectedDomain ?? ''}
          onChange={(e) => setSelectedDomain(e.target.value || null)}
        >
          <option value="">All Domains</option>
          {domains.map((d) => (
            <option key={d.domain_id} value={d.domain_id}>
              {d.domain_id} — {d.name}
            </option>
          ))}
        </select>

        {/* Clear filters */}
        {(selectedDomain || selectedLevel || searchQuery) && (
          <button
            className="btn btn-sm btn-ghost"
            onClick={() => {
              setSelectedDomain(null)
              setSelectedLevel(null)
              setSearchQuery('')
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Stats bar */}
      <div className="text-sm text-base-content/50 mb-4">
        {practices.length} practice{practices.length !== 1 ? 's' : ''} found
        {selectedDomain && ` in ${domainMap[selectedDomain]?.name ?? selectedDomain}`}
        {selectedLevel && ` at Level ${selectedLevel}`}
      </div>

      {error && (
        <div className="alert alert-error mb-4">
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <span className="loading loading-spinner loading-lg text-primary" />
        </div>
      ) : practices.length === 0 ? (
        <div className="text-center py-12 text-base-content/50">
          No practices found. Try adjusting your filters.
        </div>
      ) : (
        <div className="flex gap-6">
          {/* Practice list */}
          <div className="flex-1 space-y-6">
            {Object.entries(grouped)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([domainId, domainPractices]) => (
                <div key={domainId}>
                  <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
                    <span className="badge badge-neutral badge-sm">{domainId}</span>
                    {domainMap[domainId]?.name ?? domainId}
                    <span className="text-xs text-base-content/40 font-normal">
                      ({domainPractices.length})
                    </span>
                  </h2>

                  <div className="space-y-1">
                    {domainPractices.map((p) => (
                      <button
                        key={p.practice_id}
                        className={`w-full text-left px-4 py-3 rounded-lg border transition-colors cursor-pointer ${
                          selectedPractice?.practice_id === p.practice_id
                            ? 'border-primary bg-primary/5'
                            : 'border-base-300 hover:bg-base-200'
                        }`}
                        onClick={() => handlePracticeClick(p.practice_id)}
                      >
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono text-base-content/60">
                            {p.practice_id}
                          </code>
                          <span className={`badge badge-xs ${LEVEL_BADGES[p.level]}`}>
                            L{p.level}
                          </span>
                        </div>
                        <div className="text-sm mt-1">{p.title}</div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
          </div>

          {/* Practice detail panel */}
          {selectedPractice && (
            <div className="w-96 shrink-0">
              <div className="sticky top-6 card bg-base-100 border border-base-300 shadow-sm">
                <div className="card-body">
                  <div className="flex items-center justify-between">
                    <code className="text-sm font-mono text-primary">
                      {selectedPractice.practice_id}
                    </code>
                    <button
                      className="btn btn-ghost btn-xs"
                      onClick={() => setSelectedPractice(null)}
                    >
                      ✕
                    </button>
                  </div>

                  <h3 className="card-title text-base mt-1">{selectedPractice.title}</h3>

                  <div className="flex gap-2 mt-1">
                    <span className={`badge badge-sm ${LEVEL_BADGES[selectedPractice.level]}`}>
                      {LEVEL_NAMES[selectedPractice.level]}
                    </span>
                    <span className="badge badge-sm badge-neutral">
                      {selectedPractice.domain_ref}
                    </span>
                  </div>

                  {selectedPractice.description && (
                    <div className="mt-3">
                      <h4 className="text-xs font-semibold uppercase text-base-content/50 mb-1">
                        Description
                      </h4>
                      <p className="text-sm">{selectedPractice.description}</p>
                    </div>
                  )}

                  {selectedPractice.nist_refs && selectedPractice.nist_refs.length > 0 && (
                    <div className="mt-3">
                      <h4 className="text-xs font-semibold uppercase text-base-content/50 mb-1">
                        NIST References
                      </h4>
                      <div className="flex flex-wrap gap-1">
                        {selectedPractice.nist_refs.map((ref) => (
                          <span key={ref} className="badge badge-outline badge-xs">
                            {ref}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedPractice.assessment_objectives &&
                    selectedPractice.assessment_objectives.length > 0 && (
                      <div className="mt-3">
                        <h4 className="text-xs font-semibold uppercase text-base-content/50 mb-1">
                          Assessment Objectives
                        </h4>
                        <ul className="list-disc list-inside text-sm space-y-1">
                          {selectedPractice.assessment_objectives.map((obj, i) => (
                            <li key={i}>{obj}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                  {selectedPractice.evidence_requirements &&
                    selectedPractice.evidence_requirements.length > 0 && (
                      <div className="mt-3">
                        <h4 className="text-xs font-semibold uppercase text-base-content/50 mb-1">
                          Evidence Requirements
                        </h4>
                        <ul className="list-disc list-inside text-sm space-y-1">
                          {selectedPractice.evidence_requirements.map((req, i) => (
                            <li key={i}>{req}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
