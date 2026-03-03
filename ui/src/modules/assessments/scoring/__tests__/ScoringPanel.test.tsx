import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ScoringPanel from '../ScoringPanel'
import type { Assessment } from '@/types/assessment'

const mockAssessment: Assessment = {
  id: 'a1',
  org_id: 'org1',
  title: 'Test Assessment',
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

const domains = [
  { id: 'd1', domain_id: 'AC', name: 'Access Control', description: null },
]

const practices = [
  { id: 'p1', practice_id: 'AC.L1-001', domain_ref: 'AC', level: 1, title: 'Limit access' },
]

const evaluations = [
  {
    id: 'e1', assessment_id: 'a1', practice_id: 'AC.L1-001', status: 'met' as const,
    score: 1, assessor_notes: null, datapact_sync_status: null, datapact_sync_at: null,
    created_at: '', updated_at: '',
  },
]

describe('ScoringPanel', () => {
  it('renders all scoring widgets', () => {
    render(
      <ScoringPanel
        assessment={mockAssessment}
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />,
    )
    expect(screen.getByText('SPRS Score')).toBeDefined()
    expect(screen.getByText('Overall Compliance')).toBeDefined()
    expect(screen.getByText('Domain Compliance')).toBeDefined()
  })

  it('can be collapsed and expanded', () => {
    render(
      <ScoringPanel
        assessment={mockAssessment}
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />,
    )
    const toggle = screen.getByLabelText('Toggle scoring panel')
    // Panel is expanded by default — widgets visible
    expect(screen.getByText('SPRS Score')).toBeDefined()
    // Collapse
    fireEvent.click(toggle)
    // When collapsed, the panel content has hidden class
    const panel = screen.getByTestId('scoring-panel-content')
    expect(panel.classList.contains('hidden')).toBe(true)
    // Expand again
    fireEvent.click(toggle)
    expect(panel.classList.contains('hidden')).toBe(false)
  })

  it('renders with null scores', () => {
    render(
      <ScoringPanel
        assessment={{ ...mockAssessment, sprs_score: null, overall_score: null }}
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />,
    )
    // Should render without crashing
    expect(screen.getByText('SPRS Score')).toBeDefined()
  })
})
