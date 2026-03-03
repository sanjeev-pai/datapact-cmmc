import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import EvidencePanel from '../EvidencePanel'

const mockItems = [
  {
    id: 'ev1',
    assessment_practice_id: 'ap1',
    title: 'Doc 1',
    description: null,
    file_path: null,
    file_url: null,
    file_name: null,
    file_size: null,
    mime_type: null,
    review_status: 'pending',
    reviewer_id: null,
    reviewed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('EvidencePanel', () => {
  it('shows loading spinner then evidence list', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: mockItems, total: 1 }),
      } as Response),
    ) as typeof fetch

    render(<EvidencePanel assessmentPracticeId="ap1" editable={true} />)

    await waitFor(() => {
      expect(screen.getByText('Doc 1')).toBeDefined()
    })
  })

  it('shows upload form when editable', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0 }),
      } as Response),
    ) as typeof fetch

    render(<EvidencePanel assessmentPracticeId="ap1" editable={true} />)

    await waitFor(() => {
      expect(screen.getByText('Upload Evidence')).toBeDefined()
    })
  })

  it('hides upload form when not editable', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0 }),
      } as Response),
    ) as typeof fetch

    render(<EvidencePanel assessmentPracticeId="ap1" editable={false} />)

    await waitFor(() => {
      expect(screen.getByText('No evidence uploaded yet.')).toBeDefined()
    })
    expect(screen.queryByText('Upload Evidence')).toBeNull()
  })

  it('shows empty state when no evidence', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0 }),
      } as Response),
    ) as typeof fetch

    render(<EvidencePanel assessmentPracticeId="ap1" editable={false} />)

    await waitFor(() => {
      expect(screen.getByText('No evidence uploaded yet.')).toBeDefined()
    })
  })
})
