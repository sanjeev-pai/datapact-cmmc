import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import EvidenceListPage from './EvidenceListPage'

// Mock useAuth
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

const mockEvidence = {
  items: [
    {
      id: 'ev1',
      assessment_practice_id: 'ap1',
      title: 'Access Control Policy v3.2',
      description: 'Corporate access control policy.',
      file_path: '/uploads/access_control.pdf',
      file_url: null,
      file_name: 'access_control_policy.pdf',
      file_size: 245760,
      mime_type: 'application/pdf',
      review_status: 'pending',
      reviewer_id: null,
      reviewed_at: null,
      created_at: '2026-02-15T00:00:00Z',
      updated_at: '2026-02-15T00:00:00Z',
    },
    {
      id: 'ev2',
      assessment_practice_id: 'ap2',
      title: 'MFA Enrollment Report',
      description: 'Report showing MFA enrollment.',
      file_path: '/uploads/mfa_report.pdf',
      file_url: null,
      file_name: 'mfa_enrollment.pdf',
      file_size: 156672,
      mime_type: 'application/pdf',
      review_status: 'accepted',
      reviewer_id: 'u1',
      reviewed_at: '2026-02-20T00:00:00Z',
      created_at: '2026-02-10T00:00:00Z',
      updated_at: '2026-02-20T00:00:00Z',
    },
    {
      id: 'ev3',
      assessment_practice_id: 'ap1',
      title: 'Password Policy Screenshot',
      description: null,
      file_path: '/uploads/password.png',
      file_url: null,
      file_name: 'password_policy.png',
      file_size: 312320,
      mime_type: 'image/png',
      review_status: 'rejected',
      reviewer_id: 'u1',
      reviewed_at: '2026-02-18T00:00:00Z',
      created_at: '2026-02-12T00:00:00Z',
      updated_at: '2026-02-18T00:00:00Z',
    },
  ],
  total: 3,
}

const mockAssessments = {
  items: [
    { id: 'a1', title: 'Acme L1 Self-Assessment' },
    { id: 'a2', title: 'Pinnacle L2 Assessment' },
  ],
  total: 2,
}

const emptyResponse = { items: [], total: 0 }

function setupFetch(evidenceResponse = mockEvidence, assessmentsResponse = mockAssessments) {
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    if (urlStr.includes('/evidence')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(evidenceResponse),
      } as Response)
    }
    if (urlStr.includes('/assessments')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(assessmentsResponse),
      } as Response)
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(emptyResponse),
    } as Response)
  }) as typeof fetch
}

beforeEach(() => {
  vi.restoreAllMocks()
  mockUseAuth.mockReturnValue({ hasRole: () => true })
  setupFetch()
})

describe('EvidenceListPage', () => {
  it('renders page title and subtitle', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('Evidence')).toBeDefined()
    expect(screen.getByText(/browse and review evidence/i)).toBeDefined()
  })

  it('loads and displays evidence in table', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Access Control Policy v3.2')).toBeDefined()
    })
    expect(screen.getByText('MFA Enrollment Report')).toBeDefined()
    expect(screen.getByText('Password Policy Screenshot')).toBeDefined()
  })

  it('shows item count', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('3 items')).toBeDefined()
    })
  })

  it('displays file names as download links', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('access_control_policy.pdf')).toBeDefined()
    })
    const link = screen.getByText('access_control_policy.pdf')
    expect(link.closest('a')).toBeDefined()
    expect(link.closest('a')?.getAttribute('href')).toContain('/evidence/ev1/download')
  })

  it('displays file sizes formatted', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('240.0 KB')).toBeDefined()
    })
  })

  it('displays status badges', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      // Each status appears in both the filter dropdown and the table badge
      expect(screen.getAllByText('Pending').length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.getAllByText('Accepted').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('Rejected').length).toBeGreaterThanOrEqual(2)
  })

  it('shows accept/reject buttons for pending evidence when user can review', async () => {
    mockUseAuth.mockReturnValue({ hasRole: () => true })
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Access Control Policy v3.2')).toBeDefined()
    })
    const acceptButtons = screen.getAllByText('Accept')
    const rejectButtons = screen.getAllByText('Reject')
    // Only pending evidence (ev1) should have accept/reject buttons
    expect(acceptButtons.length).toBe(1)
    expect(rejectButtons.length).toBe(1)
  })

  it('hides review actions when user lacks review role', async () => {
    mockUseAuth.mockReturnValue({ hasRole: () => false })
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Access Control Policy v3.2')).toBeDefined()
    })
    expect(screen.queryByText('Accept')).toBeNull()
    expect(screen.queryByText('Reject')).toBeNull()
  })

  it('has filter dropdowns', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    expect(screen.getByLabelText('Filter by review status')).toBeDefined()
    expect(screen.getByLabelText('Filter by assessment')).toBeDefined()
  })

  it('populates assessment filter dropdown', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Acme L1 Self-Assessment')).toBeDefined()
    })
    expect(screen.getByText('Pinnacle L2 Assessment')).toBeDefined()
  })

  it('shows empty state when no evidence', async () => {
    setupFetch(emptyResponse)
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('No evidence found')).toBeDefined()
    })
  })

  it('shows error state on API failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('{"detail":"Server error"}'),
      } as Response),
    ) as typeof fetch

    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/failed to load evidence|server error/i)).toBeDefined()
    })
  })

  it('re-fetches evidence when status filter changes', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Access Control Policy v3.2')).toBeDefined()
    })

    const fetchCallsBefore = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length

    // Change filter
    const statusSelect = screen.getByLabelText('Filter by review status')
    fireEvent.change(statusSelect, { target: { value: 'accepted' } })

    await waitFor(() => {
      const fetchCallsAfter = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.length
      expect(fetchCallsAfter).toBeGreaterThan(fetchCallsBefore)
    })
  })

  it('shows description when available', async () => {
    render(
      <MemoryRouter>
        <EvidenceListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Corporate access control policy.')).toBeDefined()
    })
  })
})
