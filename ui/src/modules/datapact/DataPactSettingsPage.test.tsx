import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DataPactSettingsPage from './DataPactSettingsPage'

// Mock useAuth
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}))

const mockOrg = {
  id: 'org1',
  name: 'Acme Corp',
  datapact_api_url: 'http://datapact.test:8180',
  datapact_api_key: 'test-key-123',
}

const mockContracts = {
  items: [
    { id: 'c1', title: 'Alpha Contract', status: 'active', description: 'Defense contract' },
    { id: 'c2', title: 'Beta Contract', status: 'draft', description: null },
  ],
  total: 2,
}

function setupFetch(orgResponse = mockOrg, contractsResponse = mockContracts) {
  global.fetch = vi.fn((url: string | URL | Request, init?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    const method = init?.method || 'GET'

    if (urlStr.includes('/organizations/') && method === 'GET') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(orgResponse),
      } as Response)
    }
    if (urlStr.includes('/organizations/') && method === 'PATCH') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ...orgResponse, ...JSON.parse(init?.body as string || '{}') }),
      } as Response)
    }
    if (urlStr.includes('/datapact/contracts')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(contractsResponse),
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

describe('DataPactSettingsPage', () => {
  it('renders page title', async () => {
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('DataPact Integration')).toBeDefined()
    })
  })

  it('loads and displays org DataPact settings', async () => {
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const urlInput = screen.getByLabelText('DataPact API URL') as HTMLInputElement
      expect(urlInput.value).toBe('http://datapact.test:8180')
    })
  })

  it('shows warning when user has no org', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'u1', username: 'admin', email: 'admin@acme.com', org_id: null, roles: ['viewer'] },
      hasRole: () => false,
    })
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/must belong to an organization/i)).toBeDefined()
    })
  })

  it('has Save Settings and Test Connection buttons', async () => {
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Save Settings')).toBeDefined()
    })
    expect(screen.getByText('Test Connection')).toBeDefined()
  })

  it('saves settings on button click', async () => {
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect((screen.getByLabelText('DataPact API URL') as HTMLInputElement).value).toBe(
        'http://datapact.test:8180',
      )
    })

    fireEvent.click(screen.getByText('Save Settings'))

    await waitFor(() => {
      expect(screen.getByText('Settings saved')).toBeDefined()
    })
  })

  it('tests connection and shows contract preview', async () => {
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Test Connection')).toBeDefined()
    })

    fireEvent.click(screen.getByText('Test Connection'))

    await waitFor(() => {
      expect(screen.getByText(/connected/i)).toBeDefined()
    })
    // Contract preview table
    expect(screen.getByText('Alpha Contract')).toBeDefined()
    expect(screen.getByText('Beta Contract')).toBeDefined()
    expect(screen.getByText('Contracts Preview')).toBeDefined()
  })

  it('shows error on failed connection test', async () => {
    global.fetch = vi.fn((url: string | URL | Request) => {
      const urlStr = typeof url === 'string' ? url : url.toString()
      if (urlStr.includes('/datapact/contracts')) {
        return Promise.resolve({
          ok: false,
          status: 500,
          statusText: 'Server Error',
          text: () => Promise.resolve('{"detail":"Connection refused"}'),
        } as Response)
      }
      if (urlStr.includes('/organizations/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(mockOrg),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) } as Response)
    }) as typeof fetch

    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('Test Connection')).toBeDefined()
    })

    fireEvent.click(screen.getByText('Test Connection'))

    await waitFor(() => {
      expect(screen.getByText(/connection refused/i)).toBeDefined()
    })
  })

  it('has form inputs for URL and API key', async () => {
    render(
      <MemoryRouter>
        <DataPactSettingsPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByLabelText('DataPact API URL')).toBeDefined()
    })
    expect(screen.getByLabelText('API Key')).toBeDefined()
  })
})
