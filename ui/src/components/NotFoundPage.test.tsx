import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import NotFoundPage from './NotFoundPage'

describe('NotFoundPage', () => {
  it('renders 404 heading', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>
    )
    expect(screen.getByText('404')).toBeDefined()
    expect(screen.getByText('Page Not Found')).toBeDefined()
  })

  it('has navigation buttons', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>
    )
    expect(screen.getByText('Go to Dashboard')).toBeDefined()
    expect(screen.getByText('Go Back')).toBeDefined()
  })
})
