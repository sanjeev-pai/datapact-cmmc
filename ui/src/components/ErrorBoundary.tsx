import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-base-200">
          <div className="card bg-base-100 shadow-xl max-w-lg w-full">
            <div className="card-body text-center">
              <h2 className="card-title justify-center text-error text-2xl">
                Something went wrong
              </h2>
              <p className="text-base-content/70 mt-2">
                An unexpected error occurred. Please try refreshing the page.
              </p>
              {this.state.error && (
                <div className="bg-base-200 rounded-lg p-3 mt-4 text-left">
                  <code className="text-sm text-error break-all">
                    {this.state.error.message}
                  </code>
                </div>
              )}
              <div className="card-actions justify-center mt-6 gap-2">
                <button
                  className="btn btn-primary"
                  onClick={() => window.location.reload()}
                >
                  Refresh Page
                </button>
                <button
                  className="btn btn-ghost"
                  onClick={this.handleReset}
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
