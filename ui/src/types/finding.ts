export type FindingType = 'deficiency' | 'observation' | 'recommendation'
export type FindingSeverity = 'high' | 'medium' | 'low'
export type FindingStatus = 'open' | 'resolved' | 'accepted_risk'

export interface Finding {
  id: string
  assessment_id: string
  practice_id: string | null
  finding_type: FindingType
  severity: FindingSeverity
  title: string
  description: string | null
  status: FindingStatus
  created_at: string
  updated_at: string
}

export interface FindingListResponse {
  items: Finding[]
  total: number
}
