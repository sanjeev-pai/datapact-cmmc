import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders CMMC Tracker heading', () => {
    render(<App />)
    expect(screen.getByText('CMMC Tracker')).toBeDefined()
  })
})
