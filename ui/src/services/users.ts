import { api } from './api'

export interface AdminUser {
  id: string
  username: string
  email: string
  org_id: string | null
  is_active: boolean
  roles: string[]
  created_at: string
  updated_at: string
}

export async function listUsers(): Promise<AdminUser[]> {
  return api.get<AdminUser[]>('/users')
}

export async function getUser(id: string): Promise<AdminUser> {
  return api.get<AdminUser>(`/users/${id}`)
}

export async function updateUser(
  id: string,
  data: {
    username?: string
    email?: string
    is_active?: boolean
    org_id?: string
    roles?: string[]
  },
): Promise<AdminUser> {
  return api.patch<AdminUser>(`/users/${id}`, data)
}

export async function deactivateUser(id: string): Promise<void> {
  return api.del<void>(`/users/${id}`)
}
