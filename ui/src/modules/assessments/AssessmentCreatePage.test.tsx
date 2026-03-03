import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AssessmentCreatePage from './AssessmentCreatePage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', username: 'testuser', email: 'test@co.com', org_id: 'org1', is_active: true, roles: ['compliance_officer'] },
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    hasRole: () => true,
  }),
}))

beforeEach(() => {
  vi.restoreAllMocks()
  mockNavigate.mockReset()
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ id: 'new-id', title: 'Test', status: 'draft' }),
    } as Response),
  ) as typeof fetch
})

function renderPage() {
  return render(
    <MemoryRouter>
      <AssessmentCreatePage />
    </MemoryRouter>,
  )
}

describe('AssessmentCreatePage', () => {
  it('renders the form with all required fields', () => {
    renderPage()
    expect(screen.getByText('New Assessment')).toBeDefined()
    expect(screen.getByLabelText('Title')).toBeDefined()
    expect(screen.getByLabelText('Target Level')).toBeDefined()
    expect(screen.getByLabelText('Assessment Type')).toBeDefined()
    expect(screen.getByLabelText('Lead Assessor ID (optional)')).toBeDefined()
  })

  it('renders Create and Cancel buttons', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /create assessment/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDefined()
  })

  it('shows validation errors when submitting empty form', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /create assessment/i }))
    expect(screen.getByText('Title is required')).toBeDefined()
  })

  it('submits form and navigates to assessment on success', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'My Assessment' } })
    fireEvent.change(screen.getByLabelText('Target Level'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Assessment Type'), { target: { value: 'self' } })
    fireEvent.click(screen.getByRole('button', { name: /create assessment/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/assessments/new-id', { replace: true })
    })
  })

  it('shows error message on API failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: () => Promise.resolve('{"detail":"Validation error"}'),
      } as Response),
    ) as typeof fetch

    renderPage()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Test' } })
    fireEvent.change(screen.getByLabelText('Target Level'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Assessment Type'), { target: { value: 'self' } })
    fireEvent.click(screen.getByRole('button', { name: /create assessment/i }))

    await waitFor(() => {
      expect(screen.getByText('Validation error')).toBeDefined()
    })
  })

  it('navigates back to list on cancel', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/assessments')
  })

  it('disables submit button while submitting', async () => {
    let resolveRequest: (v: Response) => void
    global.fetch = vi.fn(() => new Promise<Response>((r) => { resolveRequest = r })) as typeof fetch

    renderPage()
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Test' } })
    fireEvent.change(screen.getByLabelText('Target Level'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Assessment Type'), { target: { value: 'self' } })
    fireEvent.click(screen.getByRole('button', { name: /create assessment/i }))

    expect(screen.getByText('Creating...')).toBeDefined()

    resolveRequest!({
      ok: true,
      json: () => Promise.resolve({ id: 'new-id' }),
    } as Response)
  })
})
