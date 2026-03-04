import { useCallback } from 'react'
import toast from 'react-hot-toast'
import { ApiError } from '@/services/api'

/**
 * Hook that returns an error handler for API calls.
 * Shows a toast notification for API errors.
 */
export function useApiErrorHandler() {
  const handleError = useCallback((error: unknown, fallbackMessage?: string) => {
    if (error instanceof ApiError) {
      // Don't toast 401s — auth context handles those
      if (error.status === 401) return

      const message = error.message || fallbackMessage || 'An error occurred'
      if (error.status >= 500) {
        toast.error(`Server error: ${message}`)
      } else {
        toast.error(message)
      }
    } else if (error instanceof TypeError && error.message === 'Failed to fetch') {
      toast.error('Network error — check your connection and try again.')
    } else {
      toast.error(fallbackMessage || 'An unexpected error occurred')
    }
  }, [])

  return handleError
}
