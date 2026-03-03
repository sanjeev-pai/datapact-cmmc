import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

interface FieldErrors {
  username?: string
  email?: string
  password?: string
  confirmPassword?: string
}

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)

  function validate(): boolean {
    const errors: FieldErrors = {}
    if (!username.trim()) {
      errors.username = 'Username is required'
    } else if (username.trim().length < 3) {
      errors.username = 'Username must be at least 3 characters'
    }
    if (!email.trim()) {
      errors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = 'Enter a valid email address'
    }
    if (!password) {
      errors.password = 'Password is required'
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters'
    }
    if (password && confirmPassword !== password) {
      errors.confirmPassword = 'Passwords do not match'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')

    if (!validate()) return

    setSubmitting(true)
    try {
      await register({ username: username.trim(), email: email.trim(), password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  function clearFieldError(field: keyof FieldErrors) {
    if (fieldErrors[field]) setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200 px-4">
      <div className="card w-full max-w-sm bg-base-100 shadow-lg">
        <div className="card-body">
          <div className="text-center mb-2">
            <h1 className="text-xl font-bold text-primary">CMMC Tracker</h1>
            <p className="text-sm text-base-content/50">Create your account</p>
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
                onChange={(e) => { setUsername(e.target.value); clearFieldError('username') }}
                autoComplete="username"
                autoFocus
              />
              {fieldErrors.username && (
                <span className="text-error text-xs mt-1">{fieldErrors.username}</span>
              )}
            </div>

            <div className="form-control mb-3">
              <label className="label py-1" htmlFor="email">
                <span className="label-text text-sm">Email</span>
              </label>
              <input
                id="email"
                type="email"
                className={`input input-bordered input-sm w-full ${fieldErrors.email ? 'input-error' : ''}`}
                value={email}
                onChange={(e) => { setEmail(e.target.value); clearFieldError('email') }}
                autoComplete="email"
              />
              {fieldErrors.email && (
                <span className="text-error text-xs mt-1">{fieldErrors.email}</span>
              )}
            </div>

            <div className="form-control mb-3">
              <label className="label py-1" htmlFor="password">
                <span className="label-text text-sm">Password</span>
              </label>
              <input
                id="password"
                type="password"
                className={`input input-bordered input-sm w-full ${fieldErrors.password ? 'input-error' : ''}`}
                value={password}
                onChange={(e) => { setPassword(e.target.value); clearFieldError('password') }}
                autoComplete="new-password"
              />
              {fieldErrors.password && (
                <span className="text-error text-xs mt-1">{fieldErrors.password}</span>
              )}
            </div>

            <div className="form-control mb-4">
              <label className="label py-1" htmlFor="confirmPassword">
                <span className="label-text text-sm">Confirm Password</span>
              </label>
              <input
                id="confirmPassword"
                type="password"
                className={`input input-bordered input-sm w-full ${fieldErrors.confirmPassword ? 'input-error' : ''}`}
                value={confirmPassword}
                onChange={(e) => { setConfirmPassword(e.target.value); clearFieldError('confirmPassword') }}
                autoComplete="new-password"
              />
              {fieldErrors.confirmPassword && (
                <span className="text-error text-xs mt-1">{fieldErrors.confirmPassword}</span>
              )}
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-sm w-full"
              disabled={submitting}
            >
              {submitting ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-sm text-base-content/60 mt-3">
            Already have an account?{' '}
            <Link to="/login" className="link link-primary">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
