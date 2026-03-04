import { api } from './api'

export interface Organization {
  id: string
  name: string
  cage_code: string | null
  duns_number: string | null
  target_level: number | null
  datapact_api_url: string | null
  datapact_api_key: string | null
  created_at: string
  updated_at: string
}

export async function listOrganizations(): Promise<Organization[]> {
  return api.get<Organization[]>('/organizations')
}

export async function getOrganization(id: string): Promise<Organization> {
  return api.get<Organization>(`/organizations/${id}`)
}

export async function createOrganization(data: {
  name: string
  cage_code?: string
  duns_number?: string
  target_level?: number
}): Promise<Organization> {
  return api.post<Organization>('/organizations', data)
}

export async function updateOrganization(
  id: string,
  data: {
    name?: string
    cage_code?: string
    duns_number?: string
    target_level?: number
  },
): Promise<Organization> {
  return api.patch<Organization>(`/organizations/${id}`, data)
}

export async function deleteOrganization(id: string): Promise<void> {
  return api.del<void>(`/organizations/${id}`)
}
