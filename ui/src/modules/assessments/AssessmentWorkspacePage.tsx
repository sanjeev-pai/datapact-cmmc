import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { Assessment, AssessmentPractice, AssessmentPracticeUpdate, AssessmentStatus } from '@/types/assessment'
import type { CMMCDomain, CMMCPractice } from '@/types/cmmc'
import {
  getAssessment,
  getAssessmentPractices,
  startAssessment,
  submitAssessment,
  completeAssessment,
  updatePracticeEvaluation,
} from '@/services/assessments'
import { getDomains, getPractices } from '@/services/cmmc'
import { syncAssessment as syncAssessmentApi } from '@/services/datapact'
import type { SyncResult } from '@/types/datapact'
import WorkspacePracticeList from './WorkspacePracticeList'
import WorkspacePracticeDetail from './WorkspacePracticeDetail'
import ScoringPanel from './scoring/ScoringPanel'

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

export default function AssessmentWorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [domains, setDomains] = useState<CMMCDomain[]>([])
  const [practices, setPractices] = useState<CMMCPractice[]>([])
  const [evaluations, setEvaluations] = useState<AssessmentPractice[]>([])
  const [selectedPracticeId, setSelectedPracticeId] = useState<string | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [transitioning, setTransitioning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [syncingAll, setSyncingAll] = useState(false)
  const [syncResults, setSyncResults] = useState<SyncResult[] | null>(null)

  const loadData = useCallback(async () => {
    if (!id) return
    try {
      const [assessmentData, domainsData] = await Promise.all([
        getAssessment(id),
        getDomains(),
      ])
      setAssessment(assessmentData)
      setDomains(domainsData)

      const [evalsData, practicesData] = await Promise.all([
        getAssessmentPractices(id),
        getPractices({ level: assessmentData.target_level }),
      ])
      setEvaluations(evalsData)
      setPractices(practicesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessment')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleTransition(action: 'start' | 'submit' | 'complete') {
    if (!id) return
    setTransitioning(true)
    try {
      let updated: Assessment
      if (action === 'start') updated = await startAssessment(id)
      else if (action === 'submit') updated = await submitAssessment(id)
      else updated = await completeAssessment(id)
      setAssessment(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Transition failed')
    } finally {
      setTransitioning(false)
    }
  }

  async function handleSavePractice(practiceId: string, data: AssessmentPracticeUpdate) {
    if (!id) return
    setSaving(true)
    try {
      const updated = await updatePracticeEvaluation(id, practiceId, data)
      setEvaluations((prev) =>
        prev.map((ev) => (ev.practice_id === practiceId ? updated : ev)),
      )
      // Refresh assessment to get updated scores
      const refreshed = await getAssessment(id)
      setAssessment(refreshed)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save evaluation')
    } finally {
      setSaving(false)
    }
  }

  async function handleSyncAll() {
    if (!id) return
    setSyncingAll(true)
    setSyncResults(null)
    try {
      const res = await syncAssessmentApi(id)
      setSyncResults(res.results)
      // Refresh evaluations to get updated sync statuses
      const evalsData = await getAssessmentPractices(id)
      setEvaluations(evalsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncingAll(false)
    }
  }

  async function handlePracticeSyncComplete() {
    if (!id) return
    // Refresh evaluations to get updated sync statuses
    try {
      const evalsData = await getAssessmentPractices(id)
      setEvaluations(evalsData)
    } catch {
      // Silently fail
    }
  }

  // Find the selected practice and its evaluation
  const selectedPractice = practices.find((p) => p.practice_id === selectedPracticeId) ?? null
  const selectedEvaluation = evaluations.find((ev) => ev.practice_id === selectedPracticeId)

  if (loading) {
    return (
      <div className="flex justify-center items-center h-full py-24" data-testid="workspace-loading">
        <span className="loading loading-spinner loading-lg" />
      </div>
    )
  }

  if (error && !assessment) {
    return (
      <div className="p-6">
        <div className="alert alert-error">
          <span>{error}</span>
        </div>
      </div>
    )
  }

  if (!assessment) return null

  const status = assessment.status as AssessmentStatus

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-base-300 bg-base-100 shrink-0">
        <button
          className="btn btn-ghost btn-sm btn-square"
          onClick={() => navigate('/assessments')}
          aria-label="Back to assessments"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
          </svg>
        </button>

        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold truncate">{assessment.title}</h1>
        </div>

        <span className={`badge badge-sm ${STATUS_BADGE[status]}`}>
          {STATUS_LABEL[status]}
        </span>
        <span className="badge badge-outline badge-sm">Level {assessment.target_level}</span>

        {/* Action buttons */}
        {status === 'draft' && (
          <button
            className="btn btn-primary btn-sm"
            onClick={() => handleTransition('start')}
            disabled={transitioning}
          >
            {transitioning ? 'Starting...' : 'Start Assessment'}
          </button>
        )}
        {status === 'in_progress' && (
          <button
            className="btn btn-warning btn-sm"
            onClick={() => handleTransition('submit')}
            disabled={transitioning}
          >
            {transitioning ? 'Submitting...' : 'Submit for Review'}
          </button>
        )}
        {status === 'under_review' && (
          <button
            className="btn btn-success btn-sm"
            onClick={() => handleTransition('complete')}
            disabled={transitioning}
          >
            {transitioning ? 'Completing...' : 'Mark Complete'}
          </button>
        )}

        {/* Sync All button */}
        <button
          className="btn btn-outline btn-sm"
          onClick={handleSyncAll}
          disabled={syncingAll}
          aria-label={syncingAll ? 'Syncing all practices...' : 'Sync All'}
        >
          {syncingAll ? (
            <>
              <span className="loading loading-spinner loading-xs" />
              Syncing...
            </>
          ) : (
            'Sync All'
          )}
        </button>
      </div>

      {/* Scoring panel */}
      <ScoringPanel
        assessment={assessment}
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />

      {/* Error banner */}
      {error && (
        <div className="alert alert-error rounded-none text-sm py-2">
          <span>{error}</span>
          <button className="btn btn-ghost btn-xs" onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Sync results banner */}
      {syncResults && (
        <div className="alert alert-info rounded-none text-sm py-2" data-testid="sync-results-banner">
          <span>
            Sync complete: {syncResults.filter((r) => r.status === 'success' || r.status === 'synced').length} synced,
            {' '}{syncResults.filter((r) => r.status === 'error').length} errors,
            {' '}{syncResults.filter((r) => r.status === 'skipped').length} skipped
          </span>
          <button className="btn btn-ghost btn-xs" onClick={() => setSyncResults(null)}>Dismiss</button>
        </div>
      )}

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <WorkspacePracticeList
          domains={domains}
          practices={practices}
          evaluations={evaluations}
          selectedPracticeId={selectedPracticeId}
          onSelectPractice={setSelectedPracticeId}
        />

        {selectedPractice ? (
          <WorkspacePracticeDetail
            practice={selectedPractice}
            evaluation={selectedEvaluation}
            assessmentId={id!}
            assessmentStatus={status}
            saving={saving}
            onSave={handleSavePractice}
            onSyncComplete={handlePracticeSyncComplete}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center text-base-content/40">
            <div className="text-center">
              <p className="text-lg">Select a practice</p>
              <p className="text-sm mt-1">Choose a practice from the list to begin evaluation</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
