import type {
  Assessment,
  AssessmentCreate,
  AssessmentListResponse,
  AssessmentPractice,
  AssessmentPracticeUpdate,
} from '@/types/assessment'
import { api } from './api'

export async function getAssessments(params?: {
  status?: string
  target_level?: number
  org_id?: string
}): Promise<AssessmentListResponse> {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  if (params?.target_level) query.set('target_level', String(params.target_level))
  if (params?.org_id) query.set('org_id', params.org_id)
  const qs = query.toString()
  return api.get<AssessmentListResponse>(`/assessments${qs ? `?${qs}` : ''}`)
}

export async function getAssessment(id: string): Promise<Assessment> {
  return api.get<Assessment>(`/assessments/${id}`)
}

export async function createAssessment(data: AssessmentCreate): Promise<Assessment> {
  return api.post<Assessment>('/assessments', data)
}

export async function deleteAssessment(id: string): Promise<void> {
  return api.del<void>(`/assessments/${id}`)
}

export async function startAssessment(id: string): Promise<Assessment> {
  return api.post<Assessment>(`/assessments/${id}/start`)
}

export async function submitAssessment(id: string): Promise<Assessment> {
  return api.post<Assessment>(`/assessments/${id}/submit`)
}

export async function completeAssessment(id: string): Promise<Assessment> {
  return api.post<Assessment>(`/assessments/${id}/complete`)
}

export async function getAssessmentPractices(
  assessmentId: string,
  params?: { status?: string; domain?: string },
): Promise<AssessmentPractice[]> {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  if (params?.domain) query.set('domain', params.domain)
  const qs = query.toString()
  return api.get<AssessmentPractice[]>(
    `/assessments/${assessmentId}/practices${qs ? `?${qs}` : ''}`,
  )
}

export async function updatePracticeEvaluation(
  assessmentId: string,
  practiceId: string,
  data: AssessmentPracticeUpdate,
): Promise<AssessmentPractice> {
  return api.patch<AssessmentPractice>(
    `/assessments/${assessmentId}/practices/${practiceId}`,
    data,
  )
}
