import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import CMMCLibraryPage from './CMMCLibraryPage'

const mockDomains = [
  { id: '1', domain_id: 'AC', name: 'Access Control', description: 'Limit access.' },
]

const mockPractices = [
  { id: '2', practice_id: 'AC.L1-3.1.1', domain_ref: 'AC', level: 1, title: 'Authorized Access' },
]

beforeEach(() => {
  vi.restoreAllMocks()
  global.fetch = vi.fn((url: string | URL | Request) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    if (urlStr.includes('/cmmc/domains')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockDomains) } as Response)
    }
    if (urlStr.includes('/cmmc/practices')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockPractices) } as Response)
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
  }) as typeof fetch
})

describe('CMMCLibraryPage', () => {
  it('renders page title', async () => {
    render(
      <MemoryRouter>
        <CMMCLibraryPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('CMMC Practice Library')).toBeDefined()
  })

  it('loads and displays practices', async () => {
    render(
      <MemoryRouter>
        <CMMCLibraryPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('AC.L1-3.1.1')).toBeDefined()
    })
    expect(screen.getByText('Authorized Access')).toBeDefined()
  })

  it('shows practice count', async () => {
    render(
      <MemoryRouter>
        <CMMCLibraryPage />
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText(/1 practice found/)).toBeDefined()
    })
  })
})
