export type ReviewStatus = 'pending' | 'accepted' | 'rejected'

export interface Evidence {
  id: string
  assessment_practice_id: string
  title: string
  description: string | null
  file_path: string | null
  file_url: string | null
  file_name: string | null
  file_size: number | null
  mime_type: string | null
  review_status: ReviewStatus
  reviewer_id: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface EvidenceListResponse {
  items: Evidence[]
  total: number
}
