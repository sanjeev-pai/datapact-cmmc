import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import LoginPage from './LoginPage'

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

function mockFetch(handler: (url: string, opts?: RequestInit) => Response | Promise<Response>) {
  globalThis.fetch = vi.fn((url: string | URL | Request, opts?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    return Promise.resolve(handler(urlStr, opts))
  }) as typeof fetch
}

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  // Default: no stored tokens, so AuthProvider won't call /me on mount
  mockFetch(() => ({ ok: false, status: 404, text: () => Promise.resolve('{}') }) as unknown as Response)
})

describe('LoginPage', () => {
  it('renders login form with username and password fields', async () => {
    renderLogin()
    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })
    expect(screen.getByLabelText(/password/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined()
  })

  it('renders link to register page', async () => {
    renderLogin()
    await waitFor(() => {
      expect(screen.getByText(/create an account/i)).toBeDefined()
    })
  })

  it('shows validation when submitting empty form', async () => {
    renderLogin()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined()
    })

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/username is required/i)).toBeDefined()
    })
    expect(screen.getByText(/password is required/i)).toBeDefined()
  })

  it('calls login on valid form submission', async () => {
    mockFetch((url) => {
      if (url.includes('/auth/login')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockTokens) } as Response
      }
      if (url.includes('/auth/me')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockUser) } as Response
      }
      return { ok: false, status: 404, text: () => Promise.resolve('{}') } as unknown as Response
    })

    renderLogin()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/auth/login',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ username: 'testuser', password: 'password123' }),
        }),
      )
    })
  })

  it('displays error message on login failure', async () => {
    mockFetch((url) => {
      if (url.includes('/auth/login')) {
        return {
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
          text: () => Promise.resolve('{"detail":"Invalid username or password"}'),
        } as unknown as Response
      }
      return { ok: false, status: 404, text: () => Promise.resolve('{}') } as unknown as Response
    })

    renderLogin()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'baduser')
    await user.type(screen.getByLabelText(/password/i), 'badpass')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid username or password/i)).toBeDefined()
    })
  })

  it('disables submit button while loading', async () => {
    // Make login hang indefinitely
    mockFetch((url) => {
      if (url.includes('/auth/login')) {
        return new Promise<Response>(() => {})
      }
      return { ok: false, status: 404, text: () => Promise.resolve('{}') } as unknown as Response
    })

    renderLogin()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })
  })
})
