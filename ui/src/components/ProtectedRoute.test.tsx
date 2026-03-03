import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'

// Mock useAuth hook
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

function renderWithRouter(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard Content</div>} />
          <Route path="/admin" element={<div>Admin Content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

function renderWithRoles(initialPath: string, roles: string[]) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute requiredRoles={roles} />}>
          <Route path="/admin" element={<div>Admin Content</div>} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard Content</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ProtectedRoute', () => {
  it('shows loading spinner while auth is loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true, hasRole: () => false })
    const { container } = renderWithRouter('/dashboard')
    expect(container.querySelector('.loading-spinner')).not.toBeNull()
  })

  it('redirects to /login when user is not authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, hasRole: () => false })
    renderWithRouter('/dashboard')
    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeDefined()
    })
  })

  it('renders children when user is authenticated', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', username: 'test', roles: ['viewer'] },
      loading: false,
      hasRole: (...roles: string[]) => roles.some((r) => ['viewer'].includes(r)),
    })
    renderWithRouter('/dashboard')
    await waitFor(() => {
      expect(screen.getByText('Dashboard Content')).toBeDefined()
    })
  })

  it('shows access denied when user lacks required roles', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', username: 'test', roles: ['viewer'] },
      loading: false,
      hasRole: (...roles: string[]) => roles.some((r) => ['viewer'].includes(r)),
    })
    renderWithRoles('/admin', ['system_admin', 'org_admin'])
    await waitFor(() => {
      expect(screen.getByText(/access denied/i)).toBeDefined()
    })
  })

  it('renders content when user has required role', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', username: 'admin', roles: ['system_admin'] },
      loading: false,
      hasRole: (...roles: string[]) => roles.some((r) => ['system_admin'].includes(r)),
    })
    renderWithRoles('/admin', ['system_admin', 'org_admin'])
    await waitFor(() => {
      expect(screen.getByText('Admin Content')).toBeDefined()
    })
  })
})
