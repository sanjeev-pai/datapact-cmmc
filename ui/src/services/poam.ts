import type { POAM, POAMDetail, POAMItem, POAMListResponse } from '@/types/poam'
import { api } from './api'

export async function listPoams(params?: {
  org_id?: string
  assessment_id?: string
  status?: string
}): Promise<POAMListResponse> {
  const query = new URLSearchParams()
  if (params?.org_id) query.set('org_id', params.org_id)
  if (params?.assessment_id) query.set('assessment_id', params.assessment_id)
  if (params?.status) query.set('status', params.status)
  const qs = query.toString()
  return api.get<POAMListResponse>(`/poams${qs ? `?${qs}` : ''}`)
}

export async function getPoam(id: string): Promise<POAMDetail> {
  return api.get<POAMDetail>(`/poams/${id}`)
}

export async function createPoam(data: {
  org_id: string
  title: string
  assessment_id?: string
}): Promise<POAM> {
  return api.post<POAM>('/poams', data)
}

export async function updatePoam(
  id: string,
  data: { title?: string; status?: string },
): Promise<POAM> {
  return api.patch<POAM>(`/poams/${id}`, data)
}

export async function deletePoam(id: string): Promise<void> {
  return api.del<void>(`/poams/${id}`)
}

export async function activatePoam(id: string): Promise<POAM> {
  return api.post<POAM>(`/poams/${id}/activate`, {})
}

export async function completePoam(id: string): Promise<POAM> {
  return api.post<POAM>(`/poams/${id}/complete`, {})
}

export async function updatePoamItem(
  poamId: string,
  itemId: string,
  data: {
    milestone?: string
    scheduled_completion?: string | null
    actual_completion?: string | null
    status?: string
    resources_required?: string | null
    risk_accepted?: boolean
  },
): Promise<POAMItem> {
  return api.patch<POAMItem>(`/poams/${poamId}/items/${itemId}`, data)
}

export async function generateFromAssessment(
  poamId: string,
  assessmentId: string,
): Promise<POAMItem[]> {
  return api.post<POAMItem[]>(
    `/poams/generate/${assessmentId}?poam_id=${poamId}`,
    {},
  )
}
