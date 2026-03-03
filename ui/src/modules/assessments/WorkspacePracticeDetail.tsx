import { useEffect, useState } from 'react'
import type { CMMCPractice } from '@/types/cmmc'
import type {
  AssessmentPractice,
  AssessmentPracticeUpdate,
  AssessmentStatus,
  PracticeStatus,
} from '@/types/assessment'
import EvidencePanel from '@/modules/evidence/EvidencePanel'

interface Props {
  practice: CMMCPractice
  evaluation: AssessmentPractice | undefined
  assessmentStatus: AssessmentStatus
  saving: boolean
  onSave: (practiceId: string, data: AssessmentPracticeUpdate) => void
}

const STATUS_OPTIONS: { value: PracticeStatus; label: string }[] = [
  { value: 'not_evaluated', label: 'Not Evaluated' },
  { value: 'met', label: 'Met' },
  { value: 'not_met', label: 'Not Met' },
  { value: 'partially_met', label: 'Partially Met' },
  { value: 'not_applicable', label: 'Not Applicable' },
]

export default function WorkspacePracticeDetail({
  practice,
  evaluation,
  assessmentStatus,
  saving,
  onSave,
}: Props) {
  const editable = assessmentStatus === 'in_progress'

  const [status, setStatus] = useState<PracticeStatus>(
    (evaluation?.status as PracticeStatus) ?? 'not_evaluated',
  )
  const [notes, setNotes] = useState(evaluation?.assessor_notes ?? '')

  // Sync local state when the selected practice or evaluation changes
  useEffect(() => {
    setStatus((evaluation?.status as PracticeStatus) ?? 'not_evaluated')
    setNotes(evaluation?.assessor_notes ?? '')
  }, [evaluation])

  function handleSave() {
    const data: AssessmentPracticeUpdate = { status }
    if (notes.trim()) data.assessor_notes = notes.trim()
    else data.assessor_notes = ''
    onSave(practice.practice_id, data)
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Practice header */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="badge badge-outline badge-sm font-mono">{practice.practice_id}</span>
          <span className="badge badge-ghost badge-sm">Level {practice.level}</span>
        </div>
        <h2 className="text-lg font-semibold">{practice.title}</h2>
        {practice.nist_refs && practice.nist_refs.length > 0 && (
          <p className="text-xs text-base-content/50 mt-1">
            NIST: {practice.nist_refs.join(', ')}
          </p>
        )}
      </div>

      {/* Description */}
      {practice.description && (
        <div className="mb-4">
          <h3 className="text-sm font-medium mb-1">Description</h3>
          <p className="text-sm text-base-content/80">{practice.description}</p>
        </div>
      )}

      {/* Assessment objectives */}
      {practice.assessment_objectives && practice.assessment_objectives.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium mb-1">Assessment Objectives</h3>
          <ul className="space-y-1">
            {practice.assessment_objectives.map((obj, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-base-content/80">
                <span className="text-base-content/40 mt-0.5">
                  {evaluation?.status === 'met' ? '\u2705' : '\u2B1C'}
                </span>
                {obj}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence */}
      <div className="mb-4">
        <h3 className="text-sm font-medium mb-1">Evidence</h3>
        {evaluation ? (
          <EvidencePanel
            assessmentPracticeId={evaluation.id}
            editable={editable}
          />
        ) : (
          <p className="text-sm text-base-content/50 italic">
            Save an evaluation to attach evidence.
          </p>
        )}
      </div>

      <div className="divider my-2" />

      {/* Evaluation form */}
      <div className="space-y-3">
        <div className="form-control">
          <label className="label py-1" htmlFor="practice-status">
            <span className="label-text text-sm">Status</span>
          </label>
          <select
            id="practice-status"
            aria-label="Status"
            className="select select-bordered select-sm w-full max-w-xs"
            value={status}
            onChange={(e) => setStatus(e.target.value as PracticeStatus)}
            disabled={!editable}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-control">
          <label className="label py-1" htmlFor="practice-notes">
            <span className="label-text text-sm">Assessor Notes</span>
          </label>
          <textarea
            id="practice-notes"
            aria-label="Assessor Notes"
            className="textarea textarea-bordered text-sm w-full"
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={!editable}
            placeholder="Add assessment notes..."
          />
        </div>

        {editable && (
          <button
            className="btn btn-primary btn-sm"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Evaluation'}
          </button>
        )}
      </div>
    </div>
  )
}
