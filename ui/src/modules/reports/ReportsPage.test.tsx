import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ReportsPage from './ReportsPage'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', username: 'tester', email: 't@t.com', org_id: 'org1', is_active: true, roles: ['compliance_officer'] },
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    hasRole: (...roles: string[]) => roles.includes('compliance_officer'),
  }),
}))

const mockAssessments = {
  items: [
    {
      id: 'a1',
      org_id: 'org1',
      title: 'Level 2 Self Assessment',
      target_level: 2,
      assessment_type: 'self',
      status: 'completed',
      lead_assessor_id: null,
      started_at: '2026-01-10T00:00:00',
      completed_at: '2026-02-15T00:00:00',
      overall_score: 72.5,
      sprs_score: 45,
      created_at: '2026-01-01T00:00:00',
      updated_at: '2026-02-15T00:00:00',
    },
    {
      id: 'a2',
      org_id: 'org1',
      title: 'Level 1 Quick Check',
      target_level: 1,
      assessment_type: 'self',
      status: 'in_progress',
      lead_assessor_id: null,
      started_at: '2026-02-20T00:00:00',
      completed_at: null,
      overall_score: null,
      sprs_score: null,
      created_at: '2026-02-18T00:00:00',
      updated_at: '2026-02-20T00:00:00',
    },
  ],
  total: 2,
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === 'string' ? url : url.toString()
      if (urlStr.includes('/assessments')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockAssessments),
        } as Response)
      }
      // Report downloads return blob
      if (urlStr.includes('/reports/')) {
        return Promise.resolve({
          ok: true,
          blob: () => Promise.resolve(new Blob(['test'], { type: 'text/csv' })),
        } as Response)
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response)
    })
  })

  it('renders the page header', async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Reports')).toBeDefined()
    })
    expect(screen.getByText('Download assessment and SPRS reports')).toBeDefined()
  })

  it('renders assessment report card with selector', async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Assessment Report')).toBeDefined()
    })
    expect(screen.getByText('Select Assessment')).toBeDefined()
    expect(screen.getByText('Format')).toBeDefined()
    expect(screen.getByText('Download Report')).toBeDefined()
  })

  it('renders SPRS report card when user has org', async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('SPRS Score Report')).toBeDefined()
    })
    expect(screen.getByText('Download SPRS Report (CSV)')).toBeDefined()
  })

  it('renders assessment list table', async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('All Assessments')).toBeDefined()
    })
    expect(screen.getByText('Level 2 Self Assessment')).toBeDefined()
    expect(screen.getByText('Level 1 Quick Check')).toBeDefined()
  })

  it('shows selected assessment details', async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    // The completed assessment should be auto-selected
    await waitFor(() => {
      expect(screen.getByText('Score: 73%')).toBeDefined()
    })
    expect(screen.getByText('SPRS: 45')).toBeDefined()
  })

  it('shows error when fetch fails', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        text: () => Promise.resolve('{"detail":"Internal error"}'),
      } as Response),
    )

    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Internal error')).toBeDefined()
    })
  })

  it('allows clicking table row to select assessment', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Level 1 Quick Check')).toBeDefined()
    })

    // Click on the second assessment row
    await user.click(screen.getByText('Level 1 Quick Check'))

    // The selected row should now show the L1 assessment info
    // Since we changed selection, the detail panel should update
    await waitFor(() => {
      expect(screen.getByText('Level 1')).toBeDefined()
    })
  })
})
