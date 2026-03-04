import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from './DashboardPage'

// Mock useAuth to provide a user with org_id
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', username: 'tester', email: 't@t.com', org_id: 'org1', is_active: true, roles: ['compliance_officer'] },
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    hasRole: () => true,
  }),
}))

// Mock useOrg to provide org context
vi.mock('@/hooks/useOrg', () => ({
  useOrg: () => ({
    effectiveOrgId: 'org1',
    selectedOrgId: 'org1',
    selectedOrgName: 'Test Org',
    isSystemAdmin: false,
    organizations: [],
    selectOrg: vi.fn(),
  }),
}))

const mockSummary = { level_1: 88.2, level_2: 45.0, level_3: null }

const mockSprs = {
  current: 72,
  history: [
    { assessment_id: 'a1', title: 'Q1 Assessment', sprs_score: 50, date: '2026-01-01T00:00:00Z' },
    { assessment_id: 'a2', title: 'Q2 Assessment', sprs_score: 72, date: '2026-03-01T00:00:00Z' },
  ],
}

const mockTimeline = [
  {
    id: 'a2',
    title: 'Q2 Assessment',
    status: 'completed',
    target_level: 2,
    assessment_type: 'self',
    overall_score: 45.0,
    sprs_score: 72,
    created_at: '2026-02-15T00:00:00Z',
    completed_at: '2026-03-01T00:00:00Z',
  },
  {
    id: 'a1',
    title: 'Q1 Assessment',
    status: 'completed',
    target_level: 1,
    assessment_type: 'self',
    overall_score: 88.2,
    sprs_score: 50,
    created_at: '2025-12-01T00:00:00Z',
    completed_at: '2026-01-01T00:00:00Z',
  },
]

const mockDomains = [
  { domain_id: 'AC', domain_name: 'Access Control', met: 8, total: 10, percentage: 80.0 },
  { domain_id: 'AT', domain_name: 'Awareness & Training', met: 3, total: 3, percentage: 100.0 },
]

beforeEach(() => {
  vi.restoreAllMocks()
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    if (urlStr.includes('/dashboard/summary')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSummary) } as Response)
    }
    if (urlStr.includes('/dashboard/sprs-history')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSprs) } as Response)
    }
    if (urlStr.includes('/dashboard/timeline')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTimeline) } as Response)
    }
    if (urlStr.includes('/dashboard/domain-compliance')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockDomains) } as Response)
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response)
  }) as typeof fetch
})

// Mock ResizeObserver for Recharts
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver

describe('DashboardPage', () => {
  it('renders page title', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeDefined()
    })
  })

  it('renders compliance level cards', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Level 1')).toBeDefined()
    })
    expect(screen.getByText('Level 2')).toBeDefined()
    expect(screen.getByText('Level 3')).toBeDefined()
  })

  it('displays compliance percentages', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getAllByText('88%').length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getAllByText('45%').length).toBeGreaterThanOrEqual(1)
  })

  it('displays SPRS score', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('72')).toBeDefined()
    })
    expect(screen.getByText('SPRS Score')).toBeDefined()
  })

  it('renders assessment timeline table', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Recent Assessments')).toBeDefined()
    })
    expect(screen.getByText('Q2 Assessment')).toBeDefined()
    expect(screen.getByText('Q1 Assessment')).toBeDefined()
  })

  it('shows View all link to assessments', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('View all')).toBeDefined()
    })
  })

  it('renders SPRS Score History section', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('SPRS Score History')).toBeDefined()
    })
  })

  it('renders Domain Compliance section', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Domain Compliance')).toBeDefined()
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
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeDefined()
    })
  })

  it('shows status badges for assessments', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getAllByText('completed').length).toBeGreaterThanOrEqual(1)
    })
  })
})
