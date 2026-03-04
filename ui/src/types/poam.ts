export type POAMStatus = 'draft' | 'active' | 'completed'
export type POAMItemStatus = 'open' | 'in_progress' | 'completed'

export interface POAM {
  id: string
  org_id: string
  assessment_id: string | null
  title: string
  status: POAMStatus
  created_at: string
  updated_at: string
}

export interface POAMItem {
  id: string
  poam_id: string
  finding_id: string | null
  practice_id: string | null
  milestone: string | null
  scheduled_completion: string | null
  actual_completion: string | null
  status: POAMItemStatus
  resources_required: string | null
  risk_accepted: boolean
  created_at: string
  updated_at: string
}

export interface POAMDetail extends POAM {
  items: POAMItem[]
}

export interface POAMListResponse {
  items: POAM[]
  total: number
}
