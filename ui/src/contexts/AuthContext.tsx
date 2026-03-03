import { createContext, useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { LoginRequest, RegisterRequest, User } from '@/types/auth'
import { setTokens, setOnAuthError } from '@/services/api'
import * as authService from '@/services/auth'

export interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  hasRole: (...roles: string[]) => boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const clearAuth = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setTokens(null, null)
    setUser(null)
  }, [])

  // On mount, restore tokens from localStorage and fetch user
  useEffect(() => {
    const access = localStorage.getItem('access_token')
    const refresh = localStorage.getItem('refresh_token')

    if (access && refresh) {
      setTokens(access, refresh)
      authService
        .getMe()
        .then(setUser)
        .catch(() => clearAuth())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [clearAuth])

  // Register auth error handler for 401 interceptor
  useEffect(() => {
    setOnAuthError(() => clearAuth())
    return () => setOnAuthError(null)
  }, [clearAuth])

  const login = useCallback(async (data: LoginRequest) => {
    const tokens = await authService.login(data)
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    setTokens(tokens.access_token, tokens.refresh_token)
    const me = await authService.getMe()
    setUser(me)
  }, [])

  const register = useCallback(async (data: RegisterRequest) => {
    const newUser = await authService.register(data)
    // Auto-login after registration
    const tokens = await authService.login({
      username: data.username,
      password: data.password,
    })
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    setTokens(tokens.access_token, tokens.refresh_token)
    setUser(newUser)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
  }, [clearAuth])

  const hasRole = useCallback(
    (...roles: string[]) => {
      if (!user) return false
      return roles.some((r) => user.roles.includes(r))
    },
    [user],
  )

  const value = useMemo(
    () => ({ user, loading, login, register, logout, hasRole }),
    [user, loading, login, register, logout, hasRole],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
