export interface CMMCDomain {
  id: string
  domain_id: string
  name: string
  description: string | null
}

export interface CMMCLevel {
  id: string
  level: number
  name: string
  assessment_type: string
  description: string | null
}

export interface CMMCPractice {
  id: string
  practice_id: string
  domain_ref: string
  level: number
  title: string
  description?: string | null
  assessment_objectives?: string[] | null
  evidence_requirements?: string[] | null
  nist_refs?: string[] | null
}
