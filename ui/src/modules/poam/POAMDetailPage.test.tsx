import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import POAMDetailPage from './POAMDetailPage'

vi.mock('@/services/poam', () => ({
  getPoam: vi.fn(),
  updatePoam: vi.fn(),
  activatePoam: vi.fn(),
  completePoam: vi.fn(),
  addPoamItem: vi.fn(),
  updatePoamItem: vi.fn(),
  removePoamItem: vi.fn(),
}))

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import {
  getPoam,
  updatePoam,
  activatePoam,
  addPoamItem,
  updatePoamItem,
  removePoamItem,
} from '@/services/poam'
import { useAuth } from '@/hooks/useAuth'

const mockGetPoam = getPoam as ReturnType<typeof vi.fn>
const mockUpdatePoam = updatePoam as ReturnType<typeof vi.fn>
const mockActivatePoam = activatePoam as ReturnType<typeof vi.fn>
const mockAddPoamItem = addPoamItem as ReturnType<typeof vi.fn>
const mockUpdatePoamItem = updatePoamItem as ReturnType<typeof vi.fn>
const mockRemovePoamItem = removePoamItem as ReturnType<typeof vi.fn>
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
  resources_required: 'Security team',
  risk_accepted: false,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

const ITEM_COMPLETED = {
  id: 'i2',
  poam_id: 'p1',
  finding_id: 'f1',
  practice_id: 'IA.L1-3.5.1',
  milestone: 'Deploy MFA',
  scheduled_completion: '2026-01-01',
  actual_completion: '2025-12-30',
  status: 'completed' as const,
  resources_required: null,
  risk_accepted: true,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
}

const POAM_ACTIVE = {
  id: 'p1',
  org_id: 'org1',
  assessment_id: 'a1',
  title: 'Remediation Plan Q1',
  status: 'active' as const,
  created_at: '2026-01-15T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
  items: [ITEM_OPEN, ITEM_COMPLETED],
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/poams/p1/detail']}>
      <Routes>
        <Route path="/poams/:id/detail" element={<POAMDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetPoam.mockResolvedValue(POAM_ACTIVE)
})

describe('POAMDetailPage', () => {
  it('renders header with title, status, and item counts', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Remediation Plan Q1')).toBeInTheDocument()
    })
    expect(screen.getByText('active')).toBeInTheDocument()
    expect(screen.getByText(/2 item/)).toBeInTheDocument()
    expect(screen.getByText(/1 completed/)).toBeInTheDocument()
    expect(screen.getByText(/1 overdue/)).toBeInTheDocument()
  })

  it('renders item table with all columns', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    expect(screen.getByText('Deploy MFA')).toBeInTheDocument()
    expect(screen.getByText('AC.L1-3.1.1')).toBeInTheDocument()
    expect(screen.getByText('Security team')).toBeInTheDocument()
  })

  it('shows overdue highlighting', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    expect(screen.getByText('Overdue')).toBeInTheDocument()
  })

  it('shows progress bar', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('50%')).toBeInTheDocument()
    })
    expect(screen.getByText('Progress')).toBeInTheDocument()
  })

  it('shows CSV export and kanban link buttons', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Export CSV')).toBeInTheDocument()
    })
    expect(screen.getByText('Kanban View')).toBeInTheDocument()
  })

  it('hides edit/remove actions for viewers', async () => {
    mockUseAuth.mockReturnValue(VIEWER_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
    expect(screen.queryByText('Remove')).not.toBeInTheDocument()
    expect(screen.queryByText('+ Add Item')).not.toBeInTheDocument()
  })

  it('shows add item form on button click', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('+ Add Item')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Add Item'))
    expect(screen.getByText('Add Item', { selector: 'h2' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('e.g. Deploy MFA solution')).toBeInTheDocument()
  })

  it('adds a new item', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    const newItem = { ...ITEM_OPEN, id: 'i3', milestone: 'New task' }
    mockAddPoamItem.mockResolvedValue(newItem)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('+ Add Item')).toBeInTheDocument()
    })

    await user.click(screen.getByText('+ Add Item'))
    await user.type(screen.getByPlaceholderText('e.g. Deploy MFA solution'), 'New task')
    await user.click(screen.getByText('Add Item', { selector: 'button[type="submit"]' }))

    await waitFor(() => {
      expect(mockAddPoamItem).toHaveBeenCalledWith('p1', expect.objectContaining({ milestone: 'New task' }))
    })
  })

  it('opens inline edit for an item', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Edit')
    await user.click(editButtons[0])

    // Should show inline edit form with milestone field
    expect(screen.getByDisplayValue('Implement access controls')).toBeInTheDocument()
  })

  it('saves inline edit', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockUpdatePoamItem.mockResolvedValue({ ...ITEM_OPEN, milestone: 'Updated' })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    const editButtons = screen.getAllByText('Edit')
    await user.click(editButtons[0])

    const milestoneInput = screen.getByDisplayValue('Implement access controls')
    await user.clear(milestoneInput)
    await user.type(milestoneInput, 'Updated')
    await user.click(screen.getByText('Save'))

    await waitFor(() => {
      expect(mockUpdatePoamItem).toHaveBeenCalled()
    })
  })

  it('removes an item', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockRemovePoamItem.mockResolvedValue(undefined)
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Implement access controls')).toBeInTheDocument()
    })

    const removeButtons = screen.getAllByText('Remove')
    await user.click(removeButtons[0])

    await waitFor(() => {
      expect(mockRemovePoamItem).toHaveBeenCalledWith('p1', 'i1')
    })
  })

  it('shows status transition buttons for active POAM', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    renderPage()

    await waitFor(() => {
      // Active POAM should show Complete button
      expect(screen.getByText('Complete')).toBeInTheDocument()
    })
  })

  it('activates a draft POAM', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockGetPoam.mockResolvedValue({ ...POAM_ACTIVE, status: 'draft' })
    mockActivatePoam.mockResolvedValue({ ...POAM_ACTIVE, status: 'active' })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Activate')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Activate'))

    await waitFor(() => {
      expect(mockActivatePoam).toHaveBeenCalledWith('p1')
    })
  })

  it('shows empty state when no items', async () => {
    mockUseAuth.mockReturnValue(MANAGE_USER)
    mockGetPoam.mockResolvedValue({ ...POAM_ACTIVE, items: [] })
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('No items yet')).toBeInTheDocument()
    })
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
