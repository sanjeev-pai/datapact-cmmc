import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import EvidenceUpload from '../EvidenceUpload'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('EvidenceUpload', () => {
  it('renders upload form with drop zone', () => {
    render(<EvidenceUpload assessmentPracticeId="ap1" onUploaded={vi.fn()} />)
    expect(screen.getByText('Drop file here or click to browse')).toBeDefined()
    expect(screen.getByPlaceholderText('Evidence title')).toBeDefined()
    expect(screen.getByText('Upload Evidence')).toBeDefined()
  })

  it('disables submit when title is empty', () => {
    render(<EvidenceUpload assessmentPracticeId="ap1" onUploaded={vi.fn()} />)
    const btn = screen.getByText('Upload Evidence') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('enables submit when title is filled', () => {
    render(<EvidenceUpload assessmentPracticeId="ap1" onUploaded={vi.fn()} />)
    fireEvent.change(screen.getByPlaceholderText('Evidence title'), {
      target: { value: 'My Doc' },
    })
    const btn = screen.getByText('Upload Evidence') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })

  it('submits form and calls onUploaded', async () => {
    const mockEvidence = {
      id: 'ev1',
      assessment_practice_id: 'ap1',
      title: 'My Doc',
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
    }

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockEvidence),
      } as Response),
    ) as typeof fetch

    const onUploaded = vi.fn()
    render(<EvidenceUpload assessmentPracticeId="ap1" onUploaded={onUploaded} />)

    fireEvent.change(screen.getByPlaceholderText('Evidence title'), {
      target: { value: 'My Doc' },
    })
    fireEvent.click(screen.getByText('Upload Evidence'))

    await waitFor(() => {
      expect(onUploaded).toHaveBeenCalledWith(mockEvidence)
    })
  })

  it('shows error on upload failure', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Server Error',
        text: () => Promise.resolve('{"detail":"Upload failed"}'),
      } as Response),
    ) as typeof fetch

    render(<EvidenceUpload assessmentPracticeId="ap1" onUploaded={vi.fn()} />)

    fireEvent.change(screen.getByPlaceholderText('Evidence title'), {
      target: { value: 'Bad' },
    })
    fireEvent.click(screen.getByText('Upload Evidence'))

    await waitFor(() => {
      expect(screen.getByText('Upload failed')).toBeDefined()
    })
  })
})
