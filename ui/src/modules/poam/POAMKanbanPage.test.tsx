import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import POAMKanbanPage from './POAMKanbanPage'

vi.mock('@/services/poam', () => ({
  getPoam: vi.fn(),
  updatePoamItem: vi.fn(),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import { getPoam, updatePoamItem } from '@/services/poam'
import { useAuth } from '@/hooks/useAuth'

const mockGetPoam = getPoam as ReturnType<typeof vi.fn>
const mockUpdatePoamItem = updatePoamItem as ReturnType<typeof vi.fn>
const mockUseAuth = useAuth as ReturnType<typeof vi.fn>

const MANAGE_USER = {
  user: { id: 'u1', username: 'admin', email: 'a@b.com', org_id: 'org1' },
  hasRole: () => true,
}

const VIEWER_USER = {
  user: { id: 'u2', username: 'viewer', email: 'v@b.com', org_id: 'org1' },
  hasRole: () => false,
}

const ITEM_OPEN = {
  id: 'i1',
  poam_id: 'p1',
  finding_id: null,
  practice_id: 'AC.L1-3.1.1',
  milestone: 'Implement access controls',
  scheduled_completion: '2025-01-01',
  actual_completion: null,
  status: 'open' as const,
  resources_required: null,
  risk_accepted: false,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

const ITEM_IN_PROGRESS = {
  id: 'i2',
  poam_id: 'p1',
  finding_id: 'f1',
  practice_id: 'IA.L1-3.5.1',
  milestone: 'Deploy MFA',
  scheduled_completion: '2026-06-01',
  actual_completion: null,
  status: 'in_progress' as const,
  resources_required: 'IT team',
  risk_accepted: false,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

const ITEM_COMPLETED = {
  id: 'i3',
  poam_id: 'p1',
  finding_id: null,
  practice_id: 'SC.L1-3.13.1',
  milestone: 'Firewall update',
  scheduled_completion: '2026-02-01',
  actual_completion: '2026-01-30',
  status: 'completed' as const,
  resources_required: null,
  risk_accepted: false,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

const POAM_DETAIL = {
  id: 'p1',
  org_id: 'org1',
  assessment_id: 'a1',
  title: 'Remediation Plan Q1',
  status: 'active',
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
  items: [ITEM_OPEN, ITEM_IN_PROGRESS, ITEM_COMPLETED],
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/poams/p1']}>
      <Routes>
        <Route path="/poams/:id" element={<POAMKanbanPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetPoam.mockResolvedValue(POAM_DETAIL)
})

describe('POAMKanbanPage', () => {
  it('renders kanban board with three columns', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Remediation Plan Q1')).toBeInTheDocument()
    })
    expect(screen.getByText('Open')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('renders item cards in correct columns', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    expect(screen.getByText('Deploy MFA')).toBeInTheDocument()
    expect(screen.getByText('Firewall update')).toBeInTheDocument()
  })

  it('shows overdue indicator for past-due open items', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    // ITEM_OPEN has scheduled_completion '2025-01-01' which is in the past
    expect(screen.getByText(/Overdue:/)).toBeInTheDocument()
  })

  it('shows practice IDs on cards', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('AC.L1-3.1.1')).toBeInTheDocument()
    })
    expect(screen.getByText('IA.L1-3.5.1')).toBeInTheDocument()
  })

  it('shows transition buttons for managers', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    // Open item should have "Start" button
    const startButtons = screen.getAllByText(/Start/)
    expect(startButtons.length).toBeGreaterThanOrEqual(1)
    // In-progress item should have "Complete" button
    const completeButtons = screen.getAllByText(/Complete/)
    expect(completeButtons.length).toBeGreaterThanOrEqual(1)
  })

  it('hides transition buttons for viewers', async () => {
    mockUseAuth.mockReturnValue(VIEWER_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    expect(screen.queryByText(/Start/)).not.toBeInTheDocument()
  })

  it('transitions item status via button click', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockUpdatePoamItem.mockResolvedValue({ ...ITEM_OPEN, status: 'in_progress' })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    const startButtons = screen.getAllByText(/Start/)
    await user.click(startButtons[0])

    await waitFor(() => {
      expect(mockUpdatePoamItem).toHaveBeenCalledWith('p1', 'i1', { status: 'in_progress' })
    })
  })

  it('opens detail panel on card click', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Implement access controls'))

    await waitFor(() => {
      expect(screen.getByText('Item Detail')).toBeInTheDocument()
    })
  })

  it('saves detail edits', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockUpdatePoamItem.mockResolvedValue({ ...ITEM_OPEN, milestone: 'Updated milestone' })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Implement access controls'))

    await waitFor(() => {
      expect(screen.getByText('Item Detail')).toBeInTheDocument()
    })

    const milestoneInput = screen.getByDisplayValue('Implement access controls')
    await user.clear(milestoneInput)
    await user.type(milestoneInput, 'Updated milestone')
    await user.click(screen.getByText('Save Changes'))

    await waitFor(() => {
      expect(mockUpdatePoamItem).toHaveBeenCalled()
    })
  })

  it('shows overdue count in header', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/1 overdue/)).toBeInTheDocument()
    })
  })

  it('filters by practice ID', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    const filterInput = screen.getByPlaceholderText('Filter by practice ID...')
    await user.type(filterInput, 'IA')

    // Should only show the IA practice item
    await waitFor(() => {
      expect(screen.queryByText('Implement access controls')).not.toBeInTheDocument()
    })
    expect(screen.getByText('Deploy MFA')).toBeInTheDocument()
  })

  it('shows error on load failure', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockGetPoam.mockRejectedValue(new Error('Not found'))
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Not found')).toBeInTheDocument()
    })
  })
})
