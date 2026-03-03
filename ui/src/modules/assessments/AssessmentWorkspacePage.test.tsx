import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AssessmentWorkspacePage from './AssessmentWorkspacePage'

// ---------- Test data ----------

const mockAssessment = {
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
}

const mockDomains = [
  { id: 'd1', domain_id: 'AC', name: 'Access Control', description: null },
  { id: 'd2', domain_id: 'IA', name: 'Identification & Authentication', description: null },
]

const mockPractices = [
  {
    id: 'p1',
    practice_id: 'AC.L1-001',
    domain_ref: 'AC',
    level: 1,
    title: 'Limit system access',
    description: 'Limit information system access to authorized users.',
    assessment_objectives: ['Check user accounts', 'Verify access controls'],
    nist_refs: ['3.1.1'],
  },
  {
    id: 'p2',
    practice_id: 'AC.L2-002',
    domain_ref: 'AC',
    level: 2,
    title: 'Control CUI flow',
    description: 'Control the flow of CUI.',
    assessment_objectives: ['Verify CUI flow policies'],
    nist_refs: ['3.1.3'],
  },
  {
    id: 'p3',
    practice_id: 'IA.L1-001',
    domain_ref: 'IA',
    level: 1,
    title: 'Identify users',
    description: 'Identify information system users.',
    assessment_objectives: ['Verify user identification'],
    nist_refs: ['3.5.1'],
  },
]

const mockEvaluations = [
  {
    id: 'e1',
    assessment_id: 'a1',
    practice_id: 'AC.L1-001',
    status: 'met',
    score: 1.0,
    assessor_notes: 'All controls verified',
    datapact_sync_status: null,
    datapact_sync_at: null,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
  {
    id: 'e2',
    assessment_id: 'a1',
    practice_id: 'AC.L2-002',
    status: 'not_evaluated',
    score: null,
    assessor_notes: null,
    datapact_sync_status: null,
    datapact_sync_at: null,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
  {
    id: 'e3',
    assessment_id: 'a1',
    practice_id: 'IA.L1-001',
    status: 'not_met',
    score: 0,
    assessor_notes: null,
    datapact_sync_status: null,
    datapact_sync_at: null,
    created_at: '2026-01-15T00:00:00Z',
    updated_at: '2026-01-15T00:00:00Z',
  },
]

// ---------- Helpers ----------

function renderWorkspace(assessmentOverrides = {}) {
  const assessment = { ...mockAssessment, ...assessmentOverrides }

  global.fetch = vi.fn((url: string | URL | Request, opts?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    const method = opts?.method ?? 'GET'

    if (urlStr.includes('/assessments/a1/practices') && method === 'PATCH') {
      const body = JSON.parse(opts?.body as string)
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockEvaluations[0],
            ...body,
          }),
      } as Response)
    }
    if (urlStr.includes('/assessments/a1/practices')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockEvaluations),
      } as Response)
    }
    if (urlStr.includes('/assessments/a1/start') || urlStr.includes('/assessments/a1/submit') || urlStr.includes('/assessments/a1/complete')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(assessment),
      } as Response)
    }
    if (urlStr.includes('/assessments/a1')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(assessment),
      } as Response)
    }
    if (urlStr.includes('/cmmc/domains')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockDomains),
      } as Response)
    }
    if (urlStr.includes('/cmmc/practices')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockPractices),
      } as Response)
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response)
  }) as typeof fetch

  return render(
    <MemoryRouter initialEntries={['/assessments/a1']}>
      <Routes>
        <Route path="/assessments/:id" element={<AssessmentWorkspacePage />} />
        <Route path="/assessments" element={<div>Assessment List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

// ---------- Tests ----------

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('AssessmentWorkspacePage', () => {
  it('shows loading spinner while fetching', () => {
    global.fetch = vi.fn(() => new Promise(() => {})) as typeof fetch
    render(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes>
          <Route path="/assessments/:id" element={<AssessmentWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('workspace-loading')).toBeDefined()
  })

  it('renders assessment header with title, status, level, and scoring panel', async () => {
    renderWorkspace()
    await waitFor(() => {
      expect(screen.getByText('Q1 Self Assessment')).toBeDefined()
    })
    expect(screen.getByText('In Progress')).toBeDefined()
    expect(screen.getByText('Level 2')).toBeDefined()
    // Scores rendered via ScoringPanel widgets
    expect(screen.getByText('SPRS Score')).toBeDefined()
    expect(screen.getByText('Overall Compliance')).toBeDefined()
  })

  it('renders practice list grouped by domain', async () => {
    renderWorkspace()
    await waitFor(() => {
      // Domain names appear in both practice list and scoring panel
      expect(screen.getAllByText('Access Control').length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getAllByText('Identification & Authentication').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('AC.L1-001')).toBeDefined()
    expect(screen.getByText('IA.L1-001')).toBeDefined()
  })

  it('shows placeholder when no practice selected', async () => {
    renderWorkspace()
    await waitFor(() => {
      expect(screen.getByText('Select a practice')).toBeDefined()
    })
  })

  it('shows practice detail when practice clicked', async () => {
    renderWorkspace()
    await waitFor(() => {
      expect(screen.getByText('AC.L1-001')).toBeDefined()
    })
    fireEvent.click(screen.getByText('AC.L1-001'))
    await waitFor(() => {
      // Detail panel shows description (only present in detail, not list)
      expect(screen.getByText('Limit information system access to authorized users.')).toBeDefined()
    })
    // Title appears in both list and detail — verify the detail heading exists
    expect(screen.getAllByText('Limit system access').length).toBeGreaterThanOrEqual(2)
  })

  it('shows Start Assessment button when status is draft', async () => {
    renderWorkspace({ status: 'draft' })
    await waitFor(() => {
      expect(screen.getByText('Start Assessment')).toBeDefined()
    })
  })

  it('shows Submit for Review button when status is in_progress', async () => {
    renderWorkspace({ status: 'in_progress' })
    await waitFor(() => {
      expect(screen.getByText('Submit for Review')).toBeDefined()
    })
  })

  it('shows Mark Complete button when status is under_review', async () => {
    renderWorkspace({ status: 'under_review' })
    await waitFor(() => {
      expect(screen.getByText('Mark Complete')).toBeDefined()
    })
  })

  it('disables status selector when assessment is not in_progress', async () => {
    renderWorkspace({ status: 'draft' })
    await waitFor(() => {
      expect(screen.getByText('AC.L1-001')).toBeDefined()
    })
    fireEvent.click(screen.getByText('AC.L1-001'))
    await waitFor(() => {
      expect(screen.getByLabelText('Status')).toBeDefined()
    })
    expect((screen.getByLabelText('Status') as HTMLSelectElement).disabled).toBe(true)
  })

  it('shows error alert on API failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('{"detail":"Server error"}'),
      } as Response),
    ) as typeof fetch

    render(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes>
          <Route path="/assessments/:id" element={<AssessmentWorkspacePage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeDefined()
    })
  })

  it('navigates back to assessments list', async () => {
    renderWorkspace()
    await waitFor(() => {
      expect(screen.getByText('Q1 Self Assessment')).toBeDefined()
    })
    fireEvent.click(screen.getByLabelText('Back to assessments'))
    await waitFor(() => {
      expect(screen.getByText('Assessment List')).toBeDefined()
    })
  })
})
