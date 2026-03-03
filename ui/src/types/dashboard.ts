export interface ComplianceSummary {
  level_1: number | null
  level_2: number | null
  level_3: number | null
}

export interface DomainCompliance {
  domain_id: string
  domain_name: string
  met: number
  total: number
  percentage: number
}

export interface SprsHistoryEntry {
  assessment_id: string
  title: string
  sprs_score: number
  date: string
}

export interface SprsSummary {
  current: number | null
  history: SprsHistoryEntry[]
}

export interface TimelineEntry {
  id: string
  title: string
  status: string
  target_level: number
  assessment_type: string
  overall_score: number | null
  sprs_score: number | null
  created_at: string
  completed_at: string | null
}

export interface FindingsSummary {
  total: number
  by_severity: Record<string, number>
  by_status: Record<string, number>
}
