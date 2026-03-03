import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DataPactMappingsPage from './DataPactMappingsPage'

// Mock useAuth
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

const mockMappings = {
  items: [
    {
      id: 'm1',
      org_id: 'org1',
      practice_id: 'AC.L1-3.1.1',
      datapact_contract_id: 'c1',
      datapact_contract_name: 'Alpha Contract',
      created_at: '2026-01-15T00:00:00Z',
      updated_at: '2026-01-15T00:00:00Z',
    },
  ],
  total: 1,
}

const mockContracts = {
  items: [
    { id: 'c1', title: 'Alpha Contract', status: 'active' },
    { id: 'c2', title: 'Beta Contract', status: 'draft' },
  ],
  total: 2,
}

const mockPractices = [
  { id: 'cp1', practice_id: 'AC.L1-3.1.1', domain_ref: 'AC', level: 1, title: 'Authorized Access Control' },
  { id: 'cp2', practice_id: 'AT.L1-3.2.1', domain_ref: 'AT', level: 1, title: 'Role-Based Awareness' },
]

const mockSuggestions = [
  { practice_id: 'AT.L1-3.2.1', contract_id: 'c2', contract_name: 'Beta Contract', reason: 'Domain AT keywords matched: training' },
]

function setupFetch() {
  global.fetch = vi.fn((url: string | URL | Request, init?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    const method = init?.method || 'GET'

    if (urlStr.includes('/datapact/mappings') && method === 'GET') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockMappings),
      } as Response)
    }
    if (urlStr.includes('/datapact/mappings') && method === 'POST') {
      return Promise.resolve({
        ok: true,
        status: 201,
        json: () =>
          Promise.resolve({
            id: 'm2',
            org_id: 'org1',
            ...JSON.parse(init?.body as string || '{}'),
            created_at: '2026-03-01T00:00:00Z',
            updated_at: '2026-03-01T00:00:00Z',
          }),
      } as Response)
    }
    if (urlStr.includes('/datapact/mappings/') && method === 'DELETE') {
      return Promise.resolve({
        ok: true,
        status: 204,
        json: () => Promise.resolve(null),
      } as Response)
    }
    if (urlStr.includes('/datapact/contracts')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockContracts),
      } as Response)
    }
    if (urlStr.includes('/datapact/suggest') && method === 'POST') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSuggestions),
      } as Response)
    }
    if (urlStr.includes('/cmmc/practices')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockPractices),
      } as Response)
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    } as Response)
  }) as typeof fetch
}

beforeEach(() => {
  vi.restoreAllMocks()
  mockUseAuth.mockReturnValue({
    user: { id: 'u1', username: 'admin', email: 'admin@acme.com', org_id: 'org1', roles: ['org_admin'] },
    hasRole: () => true,
  })
  setupFetch()
})

describe('DataPactMappingsPage', () => {
  it('renders page title and nav tabs', async () => {
    render(
      <MemoryRouter initialEntries={['/datapact/mappings']}>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('DataPact Integration')).toBeDefined()
    })
    expect(screen.getByText('Settings')).toBeDefined()
    expect(screen.getByText('Practice Mappings')).toBeDefined()
  })

  it('loads and displays existing mappings', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/AC\.L1-3\.1\.1/)).toBeDefined()
    })
    expect(screen.getByText('Alpha Contract')).toBeDefined()
  })

  it('shows warning when user has no org', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', username: 'admin', email: 'admin@acme.com', org_id: null, roles: ['viewer'] },
      hasRole: () => false,
    })
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/must belong to an organization/i)).toBeDefined()
    })
  })

  it('has add mapping form with selects', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByLabelText('Practice')).toBeDefined()
    })
    expect(screen.getByLabelText('Contract')).toBeDefined()
    expect(screen.getByText('Add Mapping')).toBeDefined()
  })

  it('has auto-suggest button', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Auto-Suggest')).toBeDefined()
    })
  })

  it('shows suggestions when auto-suggest is clicked', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Auto-Suggest')).toBeDefined()
    })

    fireEvent.click(screen.getByText('Auto-Suggest'))

    await waitFor(() => {
      expect(screen.getByText('Suggested Mappings (1)')).toBeDefined()
    })
    expect(screen.getByText('AT.L1-3.2.1')).toBeDefined()
    expect(screen.getByText('Accept')).toBeDefined()
  })

  it('deletes a mapping', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Alpha Contract')).toBeDefined()
    })

    fireEvent.click(screen.getByLabelText('Delete mapping AC.L1-3.1.1'))

    await waitFor(() => {
      expect(screen.queryByText('Alpha Contract')).toBeNull()
    })
  })

  it('filters mappings by domain', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Alpha Contract')).toBeDefined()
    })

    // Filter to AT domain — should hide the AC mapping
    fireEvent.change(screen.getByLabelText('Filter by domain'), { target: { value: 'AT' } })
    expect(screen.queryByText('Alpha Contract')).toBeNull()
  })

  it('shows mapping count', async () => {
    render(
      <MemoryRouter>
        <DataPactMappingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('1 mapping')).toBeDefined()
    })
  })
})
