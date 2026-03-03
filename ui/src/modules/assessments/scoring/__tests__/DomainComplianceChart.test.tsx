import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DomainComplianceChart from '../DomainComplianceChart'
import type { CMMCDomain, CMMCPractice } from '@/types/cmmc'
import type { AssessmentPractice } from '@/types/assessment'

const domains: CMMCDomain[] = [
  { id: 'd1', domain_id: 'AC', name: 'Access Control', description: null },
  { id: 'd2', domain_id: 'IA', name: 'Identification & Auth', description: null },
]

const practices: CMMCPractice[] = [
  { id: 'p1', practice_id: 'AC.L1-001', domain_ref: 'AC', level: 1, title: 'Limit access' },
  { id: 'p2', practice_id: 'AC.L2-002', domain_ref: 'AC', level: 2, title: 'Control CUI' },
  { id: 'p3', practice_id: 'IA.L1-001', domain_ref: 'IA', level: 1, title: 'Identify users' },
]

const evaluations: AssessmentPractice[] = [
  {
    id: 'e1', assessment_id: 'a1', practice_id: 'AC.L1-001', status: 'met',
    score: 1, assessor_notes: null, datapact_sync_status: null, datapact_sync_at: null,
    created_at: '', updated_at: '',
  },
  {
    id: 'e2', assessment_id: 'a1', practice_id: 'AC.L2-002', status: 'not_met',
    score: 0, assessor_notes: null, datapact_sync_status: null, datapact_sync_at: null,
    created_at: '', updated_at: '',
  },
  {
    id: 'e3', assessment_id: 'a1', practice_id: 'IA.L1-001', status: 'met',
    score: 1, assessor_notes: null, datapact_sync_status: null, datapact_sync_at: null,
    created_at: '', updated_at: '',
  },
]

describe('DomainComplianceChart', () => {
  it('renders domain names', () => {
    render(
      <DomainComplianceChart
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />,
    )
    expect(screen.getByText('Access Control')).toBeDefined()
    expect(screen.getByText('Identification & Auth')).toBeDefined()
  })

  it('renders compliance percentages', () => {
    render(
      <DomainComplianceChart
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />,
    )
    // AC: 1/2 met = 50%, IA: 1/1 met = 100%
    expect(screen.getByText('50%')).toBeDefined()
    expect(screen.getByText('100%')).toBeDefined()
  })

  it('renders empty state when no domains', () => {
    render(
      <DomainComplianceChart domains={[]} practices={[]} evaluations={[]} />,
    )
    expect(screen.getByText('No domain data')).toBeDefined()
  })

  it('renders label', () => {
    render(
      <DomainComplianceChart
        domains={domains}
        practices={practices}
        evaluations={evaluations}
      />,
    )
    expect(screen.getByText('Domain Compliance')).toBeDefined()
  })
})
