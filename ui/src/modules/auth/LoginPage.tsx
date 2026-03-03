import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ username?: string; password?: string }>({})
  const [submitting, setSubmitting] = useState(false)

  function validate(): boolean {
    const errors: { username?: string; password?: string } = {}
    if (!username.trim()) errors.username = 'Username is required'
    if (!password) errors.password = 'Password is required'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')

    if (!validate()) return

    setSubmitting(true)
    try {
      await login({ username: username.trim(), password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200 px-4">
      <div className="card w-full max-w-sm bg-base-100 shadow-lg">
        <div className="card-body">
          <div className="text-center mb-2">
            <h1 className="text-xl font-bold text-primary">CMMC Tracker</h1>
            <p className="text-sm text-base-content/50">Sign in to your account</p>
          </div>

          {error && (
            <div className="alert alert-error text-sm py-2">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-control mb-3">
              <label className="label py-1" htmlFor="username">
                <span className="label-text text-sm">Username</span>
              </label>
              <input
                id="username"
                type="text"
                className={`input input-bordered input-sm w-full ${fieldErrors.username ? 'input-error' : ''}`}
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value)
                  if (fieldErrors.username) setFieldErrors((prev) => ({ ...prev, username: undefined }))
                }}
                autoComplete="username"
                autoFocus
              />
              {fieldErrors.username && (
                <span className="text-error text-xs mt-1">{fieldErrors.username}</span>
              )}
            </div>

            <div className="form-control mb-4">
              <label className="label py-1" htmlFor="password">
                <span className="label-text text-sm">Password</span>
              </label>
              <input
                id="password"
                type="password"
                className={`input input-bordered input-sm w-full ${fieldErrors.password ? 'input-error' : ''}`}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  if (fieldErrors.password) setFieldErrors((prev) => ({ ...prev, password: undefined }))
                }}
                autoComplete="current-password"
              />
              {fieldErrors.password && (
                <span className="text-error text-xs mt-1">{fieldErrors.password}</span>
              )}
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-sm w-full"
              disabled={submitting}
            >
              {submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="text-center text-sm text-base-content/60 mt-3">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="link link-primary">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
