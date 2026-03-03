import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import EvidenceList from '../EvidenceList'
import type { Evidence } from '@/types/evidence'

const mockEvidence: Evidence[] = [
  {
    id: 'ev1',
    assessment_practice_id: 'ap1',
    title: 'SSP Document',
    description: 'System security plan',
    file_path: '/uploads/ev1/ssp.pdf',
    file_url: null,
    file_name: 'ssp.pdf',
    file_size: 102400,
    mime_type: 'application/pdf',
    review_status: 'pending',
    reviewer_id: null,
    reviewed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'ev2',
    assessment_practice_id: 'ap1',
    title: 'Policy Note',
    description: null,
    file_path: null,
    file_url: null,
    file_name: null,
    file_size: null,
    mime_type: null,
    review_status: 'accepted',
    reviewer_id: 'u1',
    reviewed_at: '2026-01-02T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
]

describe('EvidenceList', () => {
  it('renders empty state', () => {
    render(<EvidenceList items={[]} editable={false} onDeleted={vi.fn()} />)
    expect(screen.getByText('No evidence uploaded yet.')).toBeDefined()
  })

  it('renders evidence items', () => {
    render(<EvidenceList items={mockEvidence} editable={false} onDeleted={vi.fn()} />)
    expect(screen.getByText('SSP Document')).toBeDefined()
    expect(screen.getByText('Policy Note')).toBeDefined()
  })

  it('shows review status badges', () => {
    render(<EvidenceList items={mockEvidence} editable={false} onDeleted={vi.fn()} />)
    expect(screen.getByText('Pending')).toBeDefined()
    expect(screen.getByText('Accepted')).toBeDefined()
  })

  it('shows file size for items with files', () => {
    render(<EvidenceList items={mockEvidence} editable={false} onDeleted={vi.fn()} />)
    expect(screen.getByText('100.0 KB')).toBeDefined()
  })

  it('shows delete button for pending items when editable', () => {
    render(<EvidenceList items={mockEvidence} editable={true} onDeleted={vi.fn()} />)
    // Only pending evidence (ev1) gets a delete button
    expect(screen.getByLabelText('Delete SSP Document')).toBeDefined()
    // Accepted evidence (ev2) should NOT have a delete button
    expect(screen.queryByLabelText('Delete Policy Note')).toBeNull()
  })

  it('hides delete buttons when not editable', () => {
    render(<EvidenceList items={mockEvidence} editable={false} onDeleted={vi.fn()} />)
    expect(screen.queryByLabelText('Delete SSP Document')).toBeNull()
  })

  it('renders download link for items with files', () => {
    render(<EvidenceList items={mockEvidence} editable={false} onDeleted={vi.fn()} />)
    const link = screen.getByText('SSP Document') as HTMLAnchorElement
    expect(link.href).toContain('/evidence/ev1/download')
  })
})
