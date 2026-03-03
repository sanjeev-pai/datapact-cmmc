export interface User {
  id: string
  username: string
  email: string
  org_id: string | null
  is_active: boolean
  roles: string[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}
