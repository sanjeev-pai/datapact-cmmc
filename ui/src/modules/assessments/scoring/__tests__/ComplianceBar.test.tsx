import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ComplianceBar from '../ComplianceBar'

describe('ComplianceBar', () => {
  it('renders percentage value', () => {
    render(<ComplianceBar percentage={67.5} />)
    expect(screen.getByText('67.5%')).toBeDefined()
  })

  it('renders dash when percentage is null', () => {
    render(<ComplianceBar percentage={null} />)
    expect(screen.getByText('—')).toBeDefined()
  })

  it('renders 0% correctly', () => {
    render(<ComplianceBar percentage={0} />)
    expect(screen.getByText('0%')).toBeDefined()
  })

  it('renders 100% correctly', () => {
    render(<ComplianceBar percentage={100} />)
    expect(screen.getByText('100%')).toBeDefined()
  })

  it('renders label text', () => {
    render(<ComplianceBar percentage={50} />)
    expect(screen.getByText('Overall Compliance')).toBeDefined()
  })

  it('renders the progress bar element', () => {
    render(<ComplianceBar percentage={45} />)
    expect(screen.getByRole('progressbar')).toBeDefined()
  })
})
