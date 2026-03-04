import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import POAMListPage from './POAMListPage'

// Mock services
vi.mock('@/services/poam', () => ({
  listPoams: vi.fn(),
  getPoam: vi.fn(),
  createPoam: vi.fn(),
  deletePoam: vi.fn(),
  activatePoam: vi.fn(),
  completePoam: vi.fn(),
  generateFromAssessment: vi.fn(),
}))

vi.mock('@/services/assessments', () => ({
  getAssessments: vi.fn(),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import { listPoams, getPoam, createPoam, deletePoam, activatePoam } from '@/services/poam'
import { getAssessments } from '@/services/assessments'
import { useAuth } from '@/hooks/useAuth'

const mockUseAuth = useAuth as ReturnType<typeof vi.fn>
const mockListPoams = listPoams as ReturnType<typeof vi.fn>
const mockGetPoam = getPoam as ReturnType<typeof vi.fn>
const mockGetAssessments = getAssessments as ReturnType<typeof vi.fn>
const mockCreatePoam = createPoam as ReturnType<typeof vi.fn>
const mockDeletePoam = deletePoam as ReturnType<typeof vi.fn>
const mockActivatePoam = activatePoam as ReturnType<typeof vi.fn>

function renderPage() {
  return render(
    <MemoryRouter>
      <POAMListPage />
    </MemoryRouter>,
  )
}

const MANAGE_USER = {
  user: { id: 'u1', username: 'admin', email: 'a@b.com', org_id: 'org1' },
  hasRole: () => true,
}

const VIEWER_USER = {
  user: { id: 'u2', username: 'viewer', email: 'v@b.com', org_id: 'org1' },
  hasRole: () => false,
}

const POAM1 = {
  id: 'p1',
  org_id: 'org1',
  assessment_id: 'a1',
  title: 'Remediation Plan Q1',
  status: 'draft',
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

const POAM2 = {
  id: 'p2',
  org_id: 'org1',
  assessment_id: null,
  title: 'Ongoing Monitoring',
  status: 'active',
  created_at: '2026-02-01T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z',
}

const DETAIL1 = {
  ...POAM1,
  items: [
    {
      id: 'i1',
      poam_id: 'p1',
      finding_id: null,
      practice_id: null,
      milestone: null,
      scheduled_completion: '2025-01-01',
      actual_completion: null,
      status: 'open',
      resources_required: null,
      risk_accepted: false,
      created_at: '2026-01-15T00:00:00Z',
      updated_at: '2026-01-15T00:00:00Z',
    },
  ],
}

const DETAIL2 = { ...POAM2, items: [] }

beforeEach(() => {
  vi.clearAllMocks()
  mockGetAssessments.mockResolvedValue({ items: [{ id: 'a1', title: 'Assessment 1' }] })
  mockListPoams.mockResolvedValue({ items: [POAM1, POAM2], total: 2 })
  mockGetPoam.mockImplementation((id: string) => {
    if (id === 'p1') return Promise.resolve(DETAIL1)
    return Promise.resolve(DETAIL2)
  })
})

describe('POAMListPage', () => {
  it('renders page header and POA&M table', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    expect(screen.getByText('POA&M')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Remediation Plan Q1')).toBeInTheDocument()
    })
    expect(screen.getByText('Ongoing Monitoring')).toBeInTheDocument()
    expect(screen.getByText('2 POA&Ms')).toBeInTheDocument()
  })

  it('shows status badges', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Remediation Plan Q1')).toBeInTheDocument()
    })
    const badges = screen.getAllByText('Draft')
    // At least one badge (filter option + table badge)
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  it('shows overdue badge for items past due', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Remediation Plan Q1')).toBeInTheDocument()
    })
    // The overdue badge should appear with error styling
    const errorBadges = document.querySelectorAll('.badge-error')
    expect(errorBadges.length).toBeGreaterThanOrEqual(1)
    expect(errorBadges[0].textContent).toBe('1')
  })

  it('shows empty state when no POA&Ms', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockListPoams.mockResolvedValue({ items: [], total: 0 })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('No POA&Ms found')).toBeInTheDocument()
    })
  })

  it('hides action buttons for viewers', async () => {
    mockUseAuth.mockReturnValue(VIEWER_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Remediation Plan Q1')).toBeInTheDocument()
    })
    expect(screen.queryByText('+ New POA&M')).not.toBeInTheDocument()
    expect(screen.queryByText('Activate')).not.toBeInTheDocument()
    expect(screen.queryByText('Delete')).not.toBeInTheDocument()
  })

  it('shows action buttons for managers', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('+ New POA&M')).toBeInTheDocument()
    })
    expect(screen.getByText('Generate from Assessment')).toBeInTheDocument()
    expect(screen.getByText('Activate')).toBeInTheDocument()
    expect(screen.getByText('Complete')).toBeInTheDocument()
  })

  it('creates a new POA&M via form', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    const created = { ...POAM1, id: 'p3', title: 'New POA&M' }
    mockCreatePoam.mockResolvedValue(created)
    mockGetPoam.mockImplementation((id: string) => {
      if (id === 'p3') return Promise.resolve({ ...created, items: [] })
      if (id === 'p1') return Promise.resolve(DETAIL1)
      return Promise.resolve(DETAIL2)
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('+ New POA&M')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ New POA&M'))
    expect(screen.getByText('New POA&M', { selector: 'h2' })).toBeInTheDocument()

    await user.type(screen.getByRole('textbox'), 'New POA&M')
    await user.click(screen.getByText('Create'))

    await waitFor(() => {
      expect(mockCreatePoam).toHaveBeenCalledWith({
        org_id: 'org1',
        title: 'New POA&M',
        assessment_id: undefined,
      })
    })
  })

  it('deletes a draft POA&M', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockDeletePoam.mockResolvedValue(undefined)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Delete')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Delete'))

    await waitFor(() => {
      expect(mockDeletePoam).toHaveBeenCalledWith('p1')
    })
  })

  it('activates a draft POA&M', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockActivatePoam.mockResolvedValue({ ...POAM1, status: 'active' })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Activate')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Activate'))

    await waitFor(() => {
      expect(mockActivatePoam).toHaveBeenCalledWith('p1')
    })
  })

  it('shows error on load failure', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockListPoams.mockRejectedValue(new Error('Network error'))
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })
})
