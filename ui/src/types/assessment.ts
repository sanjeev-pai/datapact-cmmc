export type AssessmentStatus = 'draft' | 'in_progress' | 'under_review' | 'completed'
export type AssessmentType = 'self' | 'third_party' | 'government'

export interface Assessment {
  id: string
  org_id: string
  title: string
  target_level: number
  assessment_type: AssessmentType
  status: AssessmentStatus
  lead_assessor_id: string | null
  started_at: string | null
  completed_at: string | null
  overall_score: number | null
  sprs_score: number | null
  created_at: string
  updated_at: string
}

export interface AssessmentListResponse {
  items: Assessment[]
  total: number
}

export interface AssessmentCreate {
  org_id: string
  title: string
  target_level: number
  assessment_type: AssessmentType
  lead_assessor_id?: string
}

export type PracticeStatus = 'not_evaluated' | 'met' | 'not_met' | 'partially_met' | 'not_applicable'

export interface AssessmentPractice {
  id: string
  assessment_id: string
  practice_id: string
  status: PracticeStatus
  score: number | null
  assessor_notes: string | null
  datapact_sync_status: string | null
  datapact_sync_at: string | null
  created_at: string
  updated_at: string
}

export interface AssessmentPracticeUpdate {
  status?: PracticeStatus
  score?: number
  assessor_notes?: string
}
