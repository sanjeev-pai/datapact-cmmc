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
