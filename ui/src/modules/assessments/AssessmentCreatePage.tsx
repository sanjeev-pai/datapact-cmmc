import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { createAssessment } from '@/services/assessments'
import type { AssessmentType } from '@/types/assessment'

interface FieldErrors {
  title?: string
  target_level?: string
  assessment_type?: string
}

const LEVEL_OPTIONS = [
  { value: '', label: 'Select level...' },
  { value: '1', label: 'Level 1 — Foundational' },
  { value: '2', label: 'Level 2 — Advanced' },
  { value: '3', label: 'Level 3 — Expert' },
]

const TYPE_OPTIONS = [
  { value: '', label: 'Select type...' },
  { value: 'self', label: 'Self Assessment' },
  { value: 'third_party', label: 'Third Party (C3PAO)' },
  { value: 'government', label: 'Government (DIBCAC)' },
]

export default function AssessmentCreatePage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [title, setTitle] = useState('')
  const [targetLevel, setTargetLevel] = useState('')
  const [assessmentType, setAssessmentType] = useState('')
  const [leadAssessorId, setLeadAssessorId] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)

  function validate(): boolean {
    const errors: FieldErrors = {}
    if (!title.trim()) errors.title = 'Title is required'
    if (!targetLevel) errors.target_level = 'Target level is required'
    if (!assessmentType) errors.assessment_type = 'Assessment type is required'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  function clearFieldError(field: keyof FieldErrors) {
    if (fieldErrors[field]) setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!validate()) return

    setSubmitting(true)
    try {
      const assessment = await createAssessment({
        org_id: user!.org_id!,
        title: title.trim(),
        target_level: Number(targetLevel),
        assessment_type: assessmentType as AssessmentType,
        lead_assessor_id: leadAssessorId.trim() || undefined,
      })
      navigate(`/assessments/${assessment.id}`, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create assessment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 max-w-lg">
      <h1 className="text-2xl font-bold mb-1">New Assessment</h1>
      <p className="text-base-content/60 text-sm mb-6">
        Create a CMMC compliance assessment for your organization.
      </p>

      {error && (
        <div className="alert alert-error text-sm py-2 mb-4">{error}</div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="form-control mb-3">
          <label className="label py-1" htmlFor="title">
            <span className="label-text text-sm">Title</span>
          </label>
          <input
            id="title"
            type="text"
            className={`input input-bordered input-sm w-full ${fieldErrors.title ? 'input-error' : ''}`}
            value={title}
            onChange={(e) => { setTitle(e.target.value); clearFieldError('title') }}
            placeholder="e.g. Q1 2026 Self Assessment"
            autoFocus
          />
          {fieldErrors.title && (
            <span className="text-error text-xs mt-1">{fieldErrors.title}</span>
          )}
        </div>

        <div className="form-control mb-3">
          <label className="label py-1" htmlFor="targetLevel">
            <span className="label-text text-sm">Target Level</span>
          </label>
          <select
            id="targetLevel"
            className={`select select-bordered select-sm w-full ${fieldErrors.target_level ? 'select-error' : ''}`}
            value={targetLevel}
            onChange={(e) => { setTargetLevel(e.target.value); clearFieldError('target_level') }}
            aria-label="Target Level"
          >
            {LEVEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {fieldErrors.target_level && (
            <span className="text-error text-xs mt-1">{fieldErrors.target_level}</span>
          )}
        </div>

        <div className="form-control mb-3">
          <label className="label py-1" htmlFor="assessmentType">
            <span className="label-text text-sm">Assessment Type</span>
          </label>
          <select
            id="assessmentType"
            className={`select select-bordered select-sm w-full ${fieldErrors.assessment_type ? 'select-error' : ''}`}
            value={assessmentType}
            onChange={(e) => { setAssessmentType(e.target.value); clearFieldError('assessment_type') }}
            aria-label="Assessment Type"
          >
            {TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          {fieldErrors.assessment_type && (
            <span className="text-error text-xs mt-1">{fieldErrors.assessment_type}</span>
          )}
        </div>

        <div className="form-control mb-6">
          <label className="label py-1" htmlFor="leadAssessorId">
            <span className="label-text text-sm">Lead Assessor ID (optional)</span>
          </label>
          <input
            id="leadAssessorId"
            type="text"
            className="input input-bordered input-sm w-full"
            value={leadAssessorId}
            onChange={(e) => setLeadAssessorId(e.target.value)}
            placeholder="User ID of lead assessor"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            className="btn btn-primary btn-sm"
            disabled={submitting}
          >
            {submitting ? 'Creating...' : 'Create Assessment'}
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => navigate('/assessments')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
