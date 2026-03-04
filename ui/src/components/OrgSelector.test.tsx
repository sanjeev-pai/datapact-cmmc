import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider } from '@/contexts/AuthContext'
import { OrgProvider } from '@/contexts/OrgContext'
import OrgSelector from './OrgSelector'

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

describe('OrgSelector', () => {
  it('renders dropdown for system_admin', async () => {
    mockFetch(adminUser)

    render(
      <AuthProvider>
        <OrgProvider>
          <OrgSelector />
        </OrgProvider>
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByLabelText('Select organization')).toBeDefined()
    })

    const select = screen.getByLabelText('Select organization') as HTMLSelectElement
    // Should have "All Organizations" + 2 orgs = 3 options
    expect(select.options.length).toBe(3)
    expect(select.options[0].text).toBe('All Organizations')
    expect(select.options[1].text).toBe('Acme Corp')
    expect(select.options[2].text).toBe('Shield Inc')
  })

  it('does not render for non-admin', async () => {
    mockFetch(regularUser)

    const { container } = render(
      <AuthProvider>
        <OrgProvider>
          <OrgSelector />
        </OrgProvider>
      </AuthProvider>,
    )

    // Wait for auth to settle
    await waitFor(() => {
      // OrgSelector returns null for non-admin, so no select element
      expect(container.querySelector('select')).toBeNull()
    })
  })
})
