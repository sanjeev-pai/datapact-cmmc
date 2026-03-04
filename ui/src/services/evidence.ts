import type { Evidence, EvidenceListResponse } from '@/types/evidence'
import { api, ApiError, getAccessToken } from './api'

const BASE = '/api'

export async function uploadEvidence(data: {
  assessment_practice_id: string
  title: string
  description?: string
  file?: File
}): Promise<Evidence> {
  const formData = new FormData()
  formData.append('assessment_practice_id', data.assessment_practice_id)
  formData.append('title', data.title)
  if (data.description) formData.append('description', data.description)
  if (data.file) formData.append('file', data.file)

  const headers: Record<string, string> = {}
  const token = getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}/evidence`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!res.ok) {
    const text = await res.text()
    let detail = `${res.status} ${res.statusText}`
    try {
      const json = JSON.parse(text)
      if (json.detail) detail = json.detail
    } catch {
      // use default
    }
    throw new ApiError(res.status, detail)
  }

  return res.json()
}

export async function listEvidence(params?: {
  assessment_practice_id?: string
  assessment_id?: string
  review_status?: string
  org_id?: string
}): Promise<EvidenceListResponse> {
  const query = new URLSearchParams()
  if (params?.assessment_practice_id) query.set('assessment_practice_id', params.assessment_practice_id)
  if (params?.assessment_id) query.set('assessment_id', params.assessment_id)
  if (params?.review_status) query.set('review_status', params.review_status)
  if (params?.org_id) query.set('org_id', params.org_id)
  const qs = query.toString()
  return api.get<EvidenceListResponse>(`/evidence${qs ? `?${qs}` : ''}`)
}

export async function getEvidence(id: string): Promise<Evidence> {
  return api.get<Evidence>(`/evidence/${id}`)
}

export async function deleteEvidence(id: string): Promise<void> {
  return api.del<void>(`/evidence/${id}`)
}

export async function reviewEvidence(
  id: string,
  review_status: 'accepted' | 'rejected',
): Promise<Evidence> {
  return api.post<Evidence>(`/evidence/${id}/review`, { review_status })
}

export function getDownloadUrl(id: string): string {
  return `${BASE}/evidence/${id}/download`
}
