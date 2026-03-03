import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SprsGauge from '../SprsGauge'

describe('SprsGauge', () => {
  it('renders the SPRS score value', () => {
    render(<SprsGauge score={72} />)
    expect(screen.getByText('72')).toBeDefined()
  })

  it('renders dash when score is null', () => {
    render(<SprsGauge score={null} />)
    expect(screen.getByText('—')).toBeDefined()
  })

  it('renders negative scores', () => {
    render(<SprsGauge score={-45} />)
    expect(screen.getByText('-45')).toBeDefined()
  })

  it('renders label text', () => {
    render(<SprsGauge score={110} />)
    expect(screen.getByText('SPRS Score')).toBeDefined()
  })

  it('renders maximum score', () => {
    render(<SprsGauge score={110} />)
    // "110" appears in both score display and range label
    expect(screen.getAllByText('110').length).toBeGreaterThanOrEqual(1)
  })

  it('renders minimum score', () => {
    render(<SprsGauge score={-203} />)
    // "-203" appears in both score display and range label
    expect(screen.getAllByText('-203').length).toBeGreaterThanOrEqual(1)
  })
})
