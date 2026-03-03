import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider } from './AuthContext'
import { useAuth } from '@/hooks/useAuth'

const mockUser = {
  id: 'u1',
  username: 'testuser',
  email: 'test@example.com',
  org_id: null,
  is_active: true,
  roles: ['viewer'],
}

const mockTokens = {
  access_token: 'access-123',
  refresh_token: 'refresh-456',
  token_type: 'bearer',
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
})

function mockFetch(handler: (url: string, opts?: RequestInit) => Response | Promise<Response>) {
  globalThis.fetch = vi.fn((url: string | URL | Request, opts?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    return Promise.resolve(handler(urlStr, opts))
  }) as typeof fetch
}

// Test component that exposes auth context
function TestConsumer() {
  const { user, loading, login, logout, register, hasRole } = useAuth()

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <div data-testid="user">{user ? user.username : 'none'}</div>
      <div data-testid="has-viewer">{String(hasRole('viewer'))}</div>
      <div data-testid="has-admin">{String(hasRole('system_admin'))}</div>
      <button
        onClick={() => login({ username: 'testuser', password: 'password123' })}
      >
        Login
      </button>
      <button onClick={logout}>Logout</button>
      <button
        onClick={() =>
          register({
            username: 'newuser',
            email: 'new@example.com',
            password: 'password123',
          })
        }
      >
        Register
      </button>
    </div>
  )
}

describe('AuthContext', () => {
  it('starts with no user when no tokens in localStorage', async () => {
    mockFetch(() => ({ ok: true, status: 200, json: () => Promise.resolve({}) }) as Response)

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('none')
    })
  })

  it('restores user from localStorage tokens on mount', async () => {
    localStorage.setItem('access_token', 'stored-access')
    localStorage.setItem('refresh_token', 'stored-refresh')

    mockFetch((url) => {
      if (url.includes('/auth/me')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockUser) } as Response
      }
      return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
    })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    // Shows loading first
    expect(screen.getByText('Loading...')).toBeDefined()

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('testuser')
    })
  })

  it('clears auth when /me fails on restore', async () => {
    localStorage.setItem('access_token', 'bad-access')
    localStorage.setItem('refresh_token', 'bad-refresh')

    mockFetch(() => ({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      text: () => Promise.resolve('{"detail":"unauthorized"}'),
    }) as unknown as Response)

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('none')
    })
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('login stores tokens and fetches user', async () => {
    mockFetch((url) => {
      if (url.includes('/auth/login')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockTokens) } as Response
      }
      if (url.includes('/auth/me')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockUser) } as Response
      }
      return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
    })

    const user = userEvent.setup()

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('none')
    })

    await user.click(screen.getByText('Login'))

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('testuser')
    })
    expect(localStorage.getItem('access_token')).toBe('access-123')
    expect(localStorage.getItem('refresh_token')).toBe('refresh-456')
  })

  it('logout clears user and tokens', async () => {
    localStorage.setItem('access_token', 'stored-access')
    localStorage.setItem('refresh_token', 'stored-refresh')

    mockFetch((url) => {
      if (url.includes('/auth/me')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockUser) } as Response
      }
      return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
    })

    const user = userEvent.setup()

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('testuser')
    })

    await user.click(screen.getByText('Logout'))

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('none')
    })
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('register creates user and auto-logs in', async () => {
    const newUser = { ...mockUser, id: 'u2', username: 'newuser', email: 'new@example.com' }

    mockFetch((url) => {
      if (url.includes('/auth/register')) {
        return { ok: true, status: 201, json: () => Promise.resolve(newUser) } as Response
      }
      if (url.includes('/auth/login')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockTokens) } as Response
      }
      return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
    })

    const user = userEvent.setup()

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('none')
    })

    await user.click(screen.getByText('Register'))

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('newuser')
    })
    expect(localStorage.getItem('access_token')).toBe('access-123')
  })

  it('hasRole returns correct values', async () => {
    localStorage.setItem('access_token', 'stored-access')
    localStorage.setItem('refresh_token', 'stored-refresh')

    mockFetch((url) => {
      if (url.includes('/auth/me')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockUser) } as Response
      }
      return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
    })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('testuser')
    })

    expect(screen.getByTestId('has-viewer').textContent).toBe('true')
    expect(screen.getByTestId('has-admin').textContent).toBe('false')
  })
})

describe('useAuth outside provider', () => {
  it('throws error when used outside AuthProvider', () => {
    // Suppress React error boundary noise
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => render(<TestConsumer />)).toThrow(
      'useAuth must be used within an AuthProvider',
    )

    spy.mockRestore()
  })
})
