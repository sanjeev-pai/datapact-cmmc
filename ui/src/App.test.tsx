import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from './App'

// Mock useAuth at the hook level
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

// Mock AuthProvider to pass children through (no actual auth logic in tests)
vi.mock('@/contexts/AuthContext', () => ({
  AuthContext: { Provider: ({ children }: { children: React.ReactNode }) => children },
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
})

describe('App', () => {
  it('redirects unauthenticated users to login', async () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, hasRole: () => false, logout: vi.fn() })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText(/sign in to your account/i)).toBeDefined()
    })
  })

  it('renders CMMC Tracker heading for authenticated users', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', username: 'test', email: 'test@example.com', roles: ['viewer'] },
      loading: false,
      hasRole: () => false,
      logout: vi.fn(),
    })
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('CMMC Tracker')).toBeDefined()
    })
  })
})
