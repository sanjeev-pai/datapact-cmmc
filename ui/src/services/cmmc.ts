import type { CMMCDomain, CMMCLevel, CMMCPractice } from '@/types/cmmc'
import { api } from './api'

export async function getDomains(): Promise<CMMCDomain[]> {
  return api.get<CMMCDomain[]>('/cmmc/domains')
}

export async function getLevels(): Promise<CMMCLevel[]> {
  return api.get<CMMCLevel[]>('/cmmc/levels')
}

export async function getPractices(params?: {
  level?: number
  domain?: string
  search?: string
}): Promise<CMMCPractice[]> {
  const query = new URLSearchParams()
  if (params?.level) query.set('level', String(params.level))
  if (params?.domain) query.set('domain', params.domain)
  if (params?.search) query.set('search', params.search)
  const qs = query.toString()
  return api.get<CMMCPractice[]>(`/cmmc/practices${qs ? `?${qs}` : ''}`)
}

export async function getPractice(practiceId: string): Promise<CMMCPractice> {
  return api.get<CMMCPractice>(`/cmmc/practices/${practiceId}`)
}
