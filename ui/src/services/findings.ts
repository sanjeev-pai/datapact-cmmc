import type { Finding, FindingListResponse } from '@/types/finding'
import { api } from './api'

export async function listFindings(params?: {
  assessment_id?: string
  type?: string
  severity?: string
  status?: string
  org_id?: string
}): Promise<FindingListResponse> {
  const query = new URLSearchParams()
  if (params?.assessment_id) query.set('assessment_id', params.assessment_id)
  if (params?.type) query.set('type', params.type)
  if (params?.severity) query.set('severity', params.severity)
  if (params?.status) query.set('status', params.status)
  if (params?.org_id) query.set('org_id', params.org_id)
  const qs = query.toString()
  return api.get<FindingListResponse>(`/findings${qs ? `?${qs}` : ''}`)
}

export async function getFinding(id: string): Promise<Finding> {
  return api.get<Finding>(`/findings/${id}`)
}

export async function createFinding(data: {
  assessment_id: string
  practice_id?: string
  finding_type: string
  severity: string
  title: string
  description?: string
}): Promise<Finding> {
  return api.post<Finding>('/findings', data)
}

export async function updateFinding(
  id: string,
  data: {
    practice_id?: string
    finding_type?: string
    severity?: string
    title?: string
    description?: string
    status?: string
  },
): Promise<Finding> {
  return api.patch<Finding>(`/findings/${id}`, data)
}

export async function deleteFinding(id: string): Promise<void> {
  return api.del<void>(`/findings/${id}`)
}
