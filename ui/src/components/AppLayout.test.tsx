import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './AppLayout'

const mockLogout = vi.fn()
const mockNavigate = vi.fn()
const mockUseAuth = vi.fn()

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderLayout(user = { id: 'u1', username: 'testuser', email: 'test@example.com', roles: ['viewer'] }) {
  mockUseAuth.mockReturnValue({
    user,
    loading: false,
    logout: mockLogout,
    hasRole: (...roles: string[]) => roles.some((r) => user.roles.includes(r)),
  })

  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('AppLayout', () => {
  it('displays username in sidebar', async () => {
    renderLayout()
    await waitFor(() => {
      expect(screen.getByText('testuser')).toBeDefined()
    })
  })

  it('calls logout and navigates to /login on logout click', async () => {
    renderLayout()
    const user = userEvent.setup()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /log out/i })).toBeDefined()
    })

    await user.click(screen.getByRole('button', { name: /log out/i }))
    expect(mockLogout).toHaveBeenCalled()
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })

  it('shows standard nav items for viewer role', async () => {
    renderLayout()
    const nav = await waitFor(() => screen.getByRole('navigation'))
    expect(nav.textContent).toContain('Dashboard')
    expect(nav.textContent).toContain('CMMC Library')
    expect(nav.textContent).toContain('Assessments')
    expect(nav.textContent).not.toContain('Admin')
  })

  it('shows Admin nav item for system_admin', async () => {
    renderLayout({ id: 'u1', username: 'admin', email: 'admin@example.com', roles: ['system_admin'] })
    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeDefined()
    })
  })

  it('shows Admin nav item for org_admin', async () => {
    renderLayout({ id: 'u1', username: 'orgadmin', email: 'org@example.com', roles: ['org_admin'] })
    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeDefined()
    })
  })
})
