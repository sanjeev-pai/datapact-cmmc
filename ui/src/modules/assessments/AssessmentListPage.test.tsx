import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AssessmentListPage from './AssessmentListPage'

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

const mockAssessments = {
  items: [
    {
      id: 'a1',
      org_id: 'org1',
      title: 'Q1 Self Assessment',
      target_level: 2,
      assessment_type: 'self',
      status: 'in_progress',
      lead_assessor_id: null,
      started_at: '2026-01-15T00:00:00Z',
      completed_at: null,
      overall_score: 45.5,
      sprs_score: 72,
      created_at: '2026-01-10T00:00:00Z',
      updated_at: '2026-01-15T00:00:00Z',
    },
    {
      id: 'a2',
      org_id: 'org1',
      title: 'Third Party Audit',
      target_level: 1,
      assessment_type: 'third_party',
      status: 'completed',
      lead_assessor_id: 'u1',
      started_at: '2025-12-01T00:00:00Z',
      completed_at: '2025-12-20T00:00:00Z',
      overall_score: 100.0,
      sprs_score: 110,
      created_at: '2025-11-28T00:00:00Z',
      updated_at: '2025-12-20T00:00:00Z',
    },
  ],
  total: 2,
}

const emptyResponse = { items: [], total: 0 }

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
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(emptyResponse),
    } as Response)
  }) as typeof fetch
})

describe('AssessmentListPage', () => {
  it('renders page title', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('Assessments')).toBeDefined()
  })

  it('renders New Assessment button', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('+ New Assessment')).toBeDefined()
  })

  it('loads and displays assessments in table', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Q1 Self Assessment')).toBeDefined()
    })
    expect(screen.getByText('Third Party Audit')).toBeDefined()
  })

  it('shows assessment count', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('2 assessments')).toBeDefined()
    })
  })

  it('displays status badges', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      // "In Progress" appears in both dropdown and badge
      expect(screen.getAllByText('In Progress').length).toBeGreaterThanOrEqual(1)
    })
    // "Completed" appears in both dropdown option and table badge
    expect(screen.getAllByText('Completed').length).toBeGreaterThanOrEqual(2)
  })

  it('displays SPRS scores', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('72')).toBeDefined()
    })
    expect(screen.getByText('110')).toBeDefined()
  })

  it('displays compliance percentages', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('45.5%')).toBeDefined()
    })
    expect(screen.getByText('100%')).toBeDefined()
  })

  it('shows empty state when no assessments', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(emptyResponse),
      } as Response),
    ) as typeof fetch

    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('No assessments found')).toBeDefined()
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
        <AssessmentListPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeDefined()
    })
  })

  it('has filter dropdowns', async () => {
    render(
      <MemoryRouter>
        <AssessmentListPage />
      </MemoryRouter>,
    )
    expect(screen.getByLabelText('Filter by status')).toBeDefined()
    expect(screen.getByLabelText('Filter by level')).toBeDefined()
  })
})
