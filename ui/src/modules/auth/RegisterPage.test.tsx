import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import RegisterPage from './RegisterPage'

const mockUser = {
  id: 'u1',
  username: 'newuser',
  email: 'new@example.com',
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

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <AuthProvider>
        <RegisterPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  mockFetch(() => ({ ok: false, status: 404, text: () => Promise.resolve('{}') }) as unknown as Response)
})

describe('RegisterPage', () => {
  it('renders registration form with all fields', async () => {
    renderRegister()
    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })
    expect(screen.getByLabelText(/email/i)).toBeDefined()
    expect(screen.getByLabelText(/^password$/i)).toBeDefined()
    expect(screen.getByLabelText(/confirm password/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /create account/i })).toBeDefined()
  })

  it('renders link to login page', async () => {
    renderRegister()
    await waitFor(() => {
      expect(screen.getByText(/sign in/i)).toBeDefined()
    })
  })

  it('shows validation when submitting empty form', async () => {
    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create account/i })).toBeDefined()
    })

    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/username is required/i)).toBeDefined()
    })
    expect(screen.getByText(/email is required/i)).toBeDefined()
    expect(screen.getByText(/password is required/i)).toBeDefined()
  })

  it('validates username minimum length', async () => {
    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'ab')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/username must be at least 3 characters/i)).toBeDefined()
    })
  })

  it('validates email format', async () => {
    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/email/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/enter a valid email address/i)).toBeDefined()
    })
  })

  it('validates password minimum length', async () => {
    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'short')
    await user.type(screen.getByLabelText(/confirm password/i), 'short')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeDefined()
    })
  })

  it('validates password confirmation matches', async () => {
    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'testuser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'different456')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeDefined()
    })
  })

  it('calls register on valid form submission', async () => {
    mockFetch((url) => {
      if (url.includes('/auth/register')) {
        return { ok: true, status: 201, json: () => Promise.resolve(mockUser) } as Response
      }
      if (url.includes('/auth/login')) {
        return { ok: true, status: 200, json: () => Promise.resolve(mockTokens) } as Response
      }
      return { ok: false, status: 404, text: () => Promise.resolve('{}') } as unknown as Response
    })

    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'newuser')
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/auth/register',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ username: 'newuser', email: 'new@example.com', password: 'password123' }),
        }),
      )
    })
  })

  it('displays error message on registration failure', async () => {
    mockFetch((url) => {
      if (url.includes('/auth/register')) {
        return {
          ok: false,
          status: 409,
          statusText: 'Conflict',
          text: () => Promise.resolve('{"detail":"Username already taken"}'),
        } as unknown as Response
      }
      return { ok: false, status: 404, text: () => Promise.resolve('{}') } as unknown as Response
    })

    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'existinguser')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/username already taken/i)).toBeDefined()
    })
  })

  it('disables submit button while loading', async () => {
    mockFetch((url) => {
      if (url.includes('/auth/register')) {
        return new Promise<Response>(() => {})
      }
      return { ok: false, status: 404, text: () => Promise.resolve('{}') } as unknown as Response
    })

    renderRegister()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByLabelText(/username/i)).toBeDefined()
    })

    await user.type(screen.getByLabelText(/username/i), 'newuser')
    await user.type(screen.getByLabelText(/email/i), 'new@example.com')
    await user.type(screen.getByLabelText(/^password$/i), 'password123')
    await user.type(screen.getByLabelText(/confirm password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /creating account/i })).toBeDisabled()
    })
  })
})
