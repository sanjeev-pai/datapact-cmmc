import type { LoginRequest, RegisterRequest, TokenResponse, User } from '@/types/auth'
import { api } from './api'

export async function login(data: LoginRequest): Promise<TokenResponse> {
  return api.post<TokenResponse>('/auth/login', data)
}

export async function register(data: RegisterRequest): Promise<User> {
  return api.post<User>('/auth/register', data)
}

export async function getMe(): Promise<User> {
  return api.get<User>('/auth/me')
}

export async function refreshTokens(refresh_token: string): Promise<TokenResponse> {
  return api.post<TokenResponse>('/auth/refresh', { refresh_token })
}
