import type {
  ContractListResponse,
  MappingListResponse,
  MappingCreate,
  MappingSuggestion,
  SyncResultsResponse,
  SyncResult,
  SyncLogListResponse,
} from '@/types/datapact'
import { api } from './api'

// ── Contracts (proxy to DataPact) ───────────────────────────────────────────

export async function getContracts(): Promise<ContractListResponse> {
  return api.get<ContractListResponse>('/datapact/contracts')
}

// ── Mappings ────────────────────────────────────────────────────────────────

export async function getMappings(params?: {
  practice_id?: string
  datapact_contract_id?: string
}): Promise<MappingListResponse> {
  const query = new URLSearchParams()
  if (params?.practice_id) query.set('practice_id', params.practice_id)
  if (params?.datapact_contract_id) query.set('datapact_contract_id', params.datapact_contract_id)
  const qs = query.toString()
  return api.get<MappingListResponse>(`/datapact/mappings${qs ? `?${qs}` : ''}`)
}

export async function createMapping(data: MappingCreate): Promise<unknown> {
  return api.post('/datapact/mappings', data)
}

export async function deleteMapping(id: string): Promise<void> {
  return api.del<void>(`/datapact/mappings/${id}`)
}

// ── Suggestions ─────────────────────────────────────────────────────────────

export async function suggestMappings(): Promise<MappingSuggestion[]> {
  return api.post<MappingSuggestion[]>('/datapact/suggest')
}

// ── Sync ────────────────────────────────────────────────────────────────────

export async function syncAssessment(assessmentId: string): Promise<SyncResultsResponse> {
  return api.post<SyncResultsResponse>(`/datapact/sync/${assessmentId}`)
}

export async function syncPractice(assessmentId: string, practiceId: string): Promise<SyncResult> {
  return api.post<SyncResult>(`/datapact/sync/${assessmentId}/${practiceId}`)
}

// ── Sync Logs ───────────────────────────────────────────────────────────────

export async function getSyncLogs(params?: {
  assessment_id?: string
  limit?: number
}): Promise<SyncLogListResponse> {
  const query = new URLSearchParams()
  if (params?.assessment_id) query.set('assessment_id', params.assessment_id)
  if (params?.limit) query.set('limit', String(params.limit))
  const qs = query.toString()
  return api.get<SyncLogListResponse>(`/datapact/sync-logs${qs ? `?${qs}` : ''}`)
}
