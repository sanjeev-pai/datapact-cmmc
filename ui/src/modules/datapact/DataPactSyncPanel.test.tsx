import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import DataPactSyncPanel from './DataPactSyncPanel'

beforeEach(() => {
  vi.restoreAllMocks()
})

function setupFetch(overrides: Record<string, unknown> = {}) {
  const syncLogs = overrides.syncLogs ?? { items: [], total: 0 }
  const syncResult = overrides.syncResult ?? {
    practice_id: 'AC.L1-3.1.1',
    status: 'success',
    message: 'Synced successfully',
    compliance: null,
  }

  global.fetch = vi.fn((url: string | URL | Request, opts?: RequestInit) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    const method = opts?.method ?? 'GET'

    if (urlStr.includes('/datapact/sync/') && method === 'POST') {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(syncResult),
      } as Response)
    }
    if (urlStr.includes('/datapact/sync-logs')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(syncLogs),
      } as Response)
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    } as Response)
  }) as typeof fetch
}

describe('DataPactSyncPanel', () => {
  it('renders sync panel with sync button', () => {
    setupFetch()
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus={null}
        syncAt={null}
        onSyncComplete={vi.fn()}
      />,
    )
    expect(screen.getByText('DataPact Sync')).toBeDefined()
    expect(screen.getByRole('button', { name: /sync this practice/i })).toBeDefined()
  })

  it('shows "never synced" when syncStatus is null', () => {
    setupFetch()
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus={null}
        syncAt={null}
        onSyncComplete={vi.fn()}
      />,
    )
    expect(screen.getByText(/never synced/i)).toBeDefined()
  })

  it('shows synced status with timestamp', () => {
    setupFetch()
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus="synced"
        syncAt="2026-03-01T12:00:00Z"
        onSyncComplete={vi.fn()}
      />,
    )
    expect(screen.getByText('Synced')).toBeDefined()
    expect(screen.getByText(/3\/1\/2026/)).toBeDefined()
  })

  it('shows error status badge', () => {
    setupFetch()
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus="error"
        syncAt="2026-03-01T12:00:00Z"
        onSyncComplete={vi.fn()}
      />,
    )
    expect(screen.getByText('Error')).toBeDefined()
  })

  it('calls sync API and shows success result', async () => {
    const onSyncComplete = vi.fn()
    setupFetch()
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus={null}
        syncAt={null}
        onSyncComplete={onSyncComplete}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /sync this practice/i }))

    await waitFor(() => {
      expect(screen.getByText(/synced successfully/i)).toBeDefined()
    })
    expect(onSyncComplete).toHaveBeenCalled()
  })

  it('shows error message on sync failure', async () => {
    setupFetch({
      syncResult: {
        practice_id: 'AC.L1-3.1.1',
        status: 'error',
        message: 'Connection refused',
        compliance: null,
      },
    })
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus={null}
        syncAt={null}
        onSyncComplete={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /sync this practice/i }))

    await waitFor(() => {
      expect(screen.getByText(/connection refused/i)).toBeDefined()
    })
  })

  it('disables button while syncing', async () => {
    // Use a never-resolving promise to keep the button in syncing state
    global.fetch = vi.fn(() => new Promise(() => {})) as typeof fetch
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus={null}
        syncAt={null}
        onSyncComplete={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /sync this practice/i }))

    await waitFor(() => {
      expect(screen.getByText(/syncing/i)).toBeDefined()
    })
    expect(
      (screen.getByRole('button', { name: /syncing/i }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('loads and displays sync logs', async () => {
    setupFetch({
      syncLogs: {
        items: [
          {
            id: 'log1',
            org_id: 'org1',
            assessment_id: 'a1',
            practice_id: 'AC.L1-3.1.1',
            status: 'success',
            error_message: null,
            created_at: '2026-03-01T12:00:00Z',
          },
        ],
        total: 1,
      },
    })
    render(
      <DataPactSyncPanel
        assessmentId="a1"
        practiceId="AC.L1-3.1.1"
        syncStatus="synced"
        syncAt="2026-03-01T12:00:00Z"
        onSyncComplete={vi.fn()}
      />,
    )

    // Expand sync log
    fireEvent.click(screen.getByText(/sync history/i))

    await waitFor(() => {
      expect(screen.getByText('AC.L1-3.1.1')).toBeDefined()
    })
  })
})
