import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider } from './AuthContext'
import { OrgProvider } from './OrgContext'
import { useOrg } from '@/hooks/useOrg'

const adminUser = {
  id: 'u1',
  username: 'admin',
  email: 'admin@example.com',
  org_id: 'org1',
  is_active: true,
  roles: ['system_admin'],
}

const regularUser = {
  id: 'u2',
  username: 'regular',
  email: 'reg@example.com',
  org_id: 'org1',
  is_active: true,
  roles: ['compliance_officer'],
}

const mockOrgs = [
  { id: 'org1', name: 'Acme Corp', cage_code: null, duns_number: null, target_level: 2, datapact_api_url: null, datapact_api_key: null, created_at: '', updated_at: '' },
  { id: 'org2', name: 'Shield Inc', cage_code: null, duns_number: null, target_level: 3, datapact_api_url: null, datapact_api_key: null, created_at: '', updated_at: '' },
]

beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.setItem('access_token', 'test-token')
  localStorage.setItem('refresh_token', 'test-refresh')
})

function mockFetch(currentUser: typeof adminUser) {
  globalThis.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(currentUser) } as Response)
    }
    if (urlStr.includes('/organizations')) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(mockOrgs) } as Response)
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) } as Response)
  }) as typeof fetch
}

function TestConsumer() {
  const { isSystemAdmin, effectiveOrgId, selectedOrgId, organizations, selectOrg, selectedOrgName } = useOrg()

  return (
    <div>
      <div data-testid="is-admin">{String(isSystemAdmin)}</div>
      <div data-testid="effective-org">{effectiveOrgId ?? 'null'}</div>
      <div data-testid="selected-org">{selectedOrgId ?? 'null'}</div>
      <div data-testid="org-count">{organizations.length}</div>
      <div data-testid="org-name">{selectedOrgName ?? 'null'}</div>
      <button onClick={() => selectOrg('org2')}>Select Org2</button>
      <button onClick={() => selectOrg(null)}>Select All</button>
    </div>
  )
}

describe('OrgContext', () => {
  it('system_admin gets orgs loaded and effectiveOrgId defaults to null (all)', async () => {
    mockFetch(adminUser)

    render(
      <AuthProvider>
        <OrgProvider>
          <TestConsumer />
        </OrgProvider>
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('is-admin').textContent).toBe('true')
    })

    await waitFor(() => {
      expect(screen.getByTestId('org-count').textContent).toBe('2')
    })

    expect(screen.getByTestId('effective-org').textContent).toBe('null')
    expect(screen.getByTestId('selected-org').textContent).toBe('null')
  })

  it('system_admin can select an org', async () => {
    mockFetch(adminUser)
    const user = userEvent.setup()

    render(
      <AuthProvider>
        <OrgProvider>
          <TestConsumer />
        </OrgProvider>
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('is-admin').textContent).toBe('true')
    })

    await user.click(screen.getByText('Select Org2'))

    expect(screen.getByTestId('effective-org').textContent).toBe('org2')
    expect(screen.getByTestId('selected-org').textContent).toBe('org2')
    expect(screen.getByTestId('org-name').textContent).toBe('Shield Inc')
  })

  it('system_admin can select all orgs', async () => {
    mockFetch(adminUser)
    const user = userEvent.setup()

    render(
      <AuthProvider>
        <OrgProvider>
          <TestConsumer />
        </OrgProvider>
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('is-admin').textContent).toBe('true')
    })

    // Select org2 first, then select all
    await user.click(screen.getByText('Select Org2'))
    expect(screen.getByTestId('effective-org').textContent).toBe('org2')

    await user.click(screen.getByText('Select All'))
    expect(screen.getByTestId('effective-org').textContent).toBe('null')
  })

  it('non-admin gets own org_id as effectiveOrgId', async () => {
    mockFetch(regularUser)

    render(
      <AuthProvider>
        <OrgProvider>
          <TestConsumer />
        </OrgProvider>
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('is-admin').textContent).toBe('false')
    })

    expect(screen.getByTestId('effective-org').textContent).toBe('org1')
    expect(screen.getByTestId('org-count').textContent).toBe('0')
  })
})

describe('useOrg outside provider', () => {
  it('throws error when used outside OrgProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => render(<TestConsumer />)).toThrow(
      'useOrg must be used within an OrgProvider',
    )

    spy.mockRestore()
  })
})
