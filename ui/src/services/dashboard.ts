import type {
  ComplianceSummary,
  DomainCompliance,
  FindingsSummary,
  SprsSummary,
  TimelineEntry,
} from '@/types/dashboard'
import { api } from './api'

export async function getComplianceSummary(orgId?: string | null): Promise<ComplianceSummary> {
  const params = orgId ? `?org_id=${encodeURIComponent(orgId)}` : ''
  return api.get<ComplianceSummary>(`/dashboard/summary${params}`)
}

export async function getDomainCompliance(assessmentId: string): Promise<DomainCompliance[]> {
  return api.get<DomainCompliance[]>(`/dashboard/domain-compliance/${assessmentId}`)
}

export async function getSprsHistory(orgId: string): Promise<SprsSummary> {
  return api.get<SprsSummary>(`/dashboard/sprs-history/${orgId}`)
}

export async function getTimeline(orgId: string, limit = 10): Promise<TimelineEntry[]> {
  return api.get<TimelineEntry[]>(`/dashboard/timeline/${orgId}?limit=${limit}`)
}

export async function getFindingsSummary(assessmentId: string): Promise<FindingsSummary> {
  return api.get<FindingsSummary>(`/dashboard/findings-summary/${assessmentId}`)
}
