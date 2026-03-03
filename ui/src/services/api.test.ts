import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api, setTokens, setOnAuthError, ApiError } from './api'

beforeEach(() => {
  vi.restoreAllMocks()
  setTokens(null, null)
  setOnAuthError(null)
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
})

function mockFetch(handler: (url: string, opts?: RequestInit) => Response | Promise<Response>) {
  globalThis.fetch = vi.fn((url: string | URL | Request, opts?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    return Promise.resolve(handler(urlStr, opts))
  }) as typeof fetch
}

describe('api', () => {
  describe('get', () => {
    it('makes GET request and returns JSON', async () => {
      mockFetch(() => ({ ok: true, status: 200, json: () => Promise.resolve({ data: 1 }) }) as Response)
      const result = await api.get('/test')
      expect(result).toEqual({ data: 1 })
      expect(fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({ method: 'GET' }))
    })

    it('throws ApiError on non-ok response', async () => {
      mockFetch(
        () =>
          ({
            ok: false,
            status: 404,
            statusText: 'Not Found',
            text: () => Promise.resolve('{"detail":"not found"}'),
          }) as unknown as Response,
      )
      await expect(api.get('/missing')).rejects.toThrow(ApiError)
      await expect(api.get('/missing')).rejects.toThrow('not found')
    })
  })

  describe('post', () => {
    it('sends JSON body', async () => {
      mockFetch((_url, opts) => {
        expect(opts?.headers).toHaveProperty('Content-Type', 'application/json')
        expect(opts?.body).toBe(JSON.stringify({ foo: 'bar' }))
        return { ok: true, status: 200, json: () => Promise.resolve({ ok: true }) } as Response
      })
      await api.post('/test', { foo: 'bar' })
    })
  })

  describe('auth headers', () => {
    it('attaches Authorization header when token is set', async () => {
      setTokens('my-token', 'my-refresh')
      mockFetch((_url, opts) => {
        expect(opts?.headers).toHaveProperty('Authorization', 'Bearer my-token')
        return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
      })
      await api.get('/secure')
    })

    it('does not attach Authorization when no token', async () => {
      mockFetch((_url, opts) => {
        expect(opts?.headers).not.toHaveProperty('Authorization')
        return { ok: true, status: 200, json: () => Promise.resolve({}) } as Response
      })
      await api.get('/public')
    })
  })

  describe('401 token refresh', () => {
    it('retries after successful refresh', async () => {
      setTokens('expired-token', 'valid-refresh')
      let callCount = 0
      mockFetch((url, opts) => {
        if (url.includes('/auth/refresh')) {
          return {
            ok: true,
            status: 200,
            json: () =>
              Promise.resolve({
                access_token: 'new-access',
                refresh_token: 'new-refresh',
              }),
          } as Response
        }
        callCount++
        if (callCount === 1) {
          return {
            ok: false,
            status: 401,
            statusText: 'Unauthorized',
            text: () => Promise.resolve('{"detail":"token expired"}'),
          } as unknown as Response
        }
        // Retry succeeds
        expect((opts?.headers as Record<string, string>)?.Authorization).toBe('Bearer new-access')
        return { ok: true, status: 200, json: () => Promise.resolve({ data: 'ok' }) } as Response
      })

      const result = await api.get('/secure')
      expect(result).toEqual({ data: 'ok' })
      expect(localStorage.getItem('access_token')).toBe('new-access')
      expect(localStorage.getItem('refresh_token')).toBe('new-refresh')
    })

    it('calls onAuthError when refresh fails', async () => {
      setTokens('expired-token', 'bad-refresh')
      const handler = vi.fn()
      setOnAuthError(handler)

      mockFetch((url) => {
        if (url.includes('/auth/refresh')) {
          return { ok: false, status: 401, statusText: 'Unauthorized' } as Response
        }
        return {
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
          text: () => Promise.resolve('{"detail":"unauthorized"}'),
        } as unknown as Response
      })

      await expect(api.get('/secure')).rejects.toThrow(ApiError)
      expect(handler).toHaveBeenCalled()
    })
  })

  describe('patch', () => {
    it('sends PATCH request with body', async () => {
      mockFetch((_url, opts) => {
        expect(opts?.method).toBe('PATCH')
        return { ok: true, status: 200, json: () => Promise.resolve({ updated: true }) } as Response
      })
      const result = await api.patch('/items/1', { name: 'new' })
      expect(result).toEqual({ updated: true })
    })
  })

  describe('del', () => {
    it('sends DELETE request', async () => {
      mockFetch((_url, opts) => {
        expect(opts?.method).toBe('DELETE')
        return { ok: true, status: 204 } as unknown as Response
      })
      await api.del('/items/1')
    })
  })
})
