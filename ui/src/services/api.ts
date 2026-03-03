const BASE = '/api'

let accessToken: string | null = null
let refreshToken: string | null = null
let onAuthError: (() => void) | null = null
let refreshPromise: Promise<boolean> | null = null

export function setTokens(access: string | null, refresh: string | null) {
  accessToken = access
  refreshToken = refresh
}

export function getAccessToken(): string | null {
  return accessToken
}

export function getRefreshToken(): string | null {
  return refreshToken
}

export function setOnAuthError(handler: (() => void) | null) {
  onAuthError = handler
}

function authHeaders(): Record<string, string> {
  if (accessToken) {
    return { Authorization: `Bearer ${accessToken}` }
  }
  return {}
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false

  // Deduplicate concurrent refresh attempts
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) return false
      const data = await res.json()
      accessToken = data.access_token
      refreshToken = data.refresh_token
      // Persist refreshed tokens
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${BASE}${path}`
  const headers: Record<string, string> = {
    ...authHeaders(),
  }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  // Auto-refresh on 401
  if (res.status === 401 && refreshToken) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      const retryHeaders: Record<string, string> = {
        ...authHeaders(),
      }
      if (body !== undefined) {
        retryHeaders['Content-Type'] = 'application/json'
      }
      res = await fetch(url, {
        method,
        headers: retryHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      })
    }
  }

  if (res.status === 401) {
    onAuthError?.()
    throw new ApiError(401, 'Unauthorized')
  }

  if (!res.ok) {
    const text = await res.text()
    let detail = `${res.status} ${res.statusText}`
    try {
      const json = JSON.parse(text)
      if (json.detail) detail = json.detail
    } catch {
      // use default detail
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function get<T>(path: string): Promise<T> {
  return request<T>('GET', path)
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('POST', path, body)
}

async function patch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('PATCH', path, body)
}

async function del<T>(path: string): Promise<T> {
  return request<T>('DELETE', path)
}

export const api = { get, post, patch, del }
