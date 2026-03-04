import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from './ErrorBoundary'

function ThrowingComponent() {
  throw new Error('Test error message')
}

function GoodComponent() {
  return <div>Working fine</div>
}

describe('ErrorBoundary', () => {
  // Suppress React error boundary console.error in tests
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = originalError
  })

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <GoodComponent />
      </ErrorBoundary>
    )
    expect(screen.getByText('Working fine')).toBeDefined()
  })

  it('renders error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    )
    expect(screen.getByText('Something went wrong')).toBeDefined()
    expect(screen.getByText('Test error message')).toBeDefined()
  })

  it('shows Refresh Page button on error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    )
    expect(screen.getByText('Refresh Page')).toBeDefined()
  })

  it('has Try Again button on error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    )
    expect(screen.getByText('Try Again')).toBeDefined()
  })
})
