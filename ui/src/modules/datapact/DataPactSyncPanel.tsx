import { useCallback, useEffect, useState } from 'react'
import { syncPractice, getSyncLogs } from '@/services/datapact'
import type { SyncResult, SyncLog } from '@/types/datapact'

interface Props {
  assessmentId: string
  practiceId: string
  syncStatus: string | null
  syncAt: string | null
  onSyncComplete: () => void
}

const STATUS_BADGE: Record<string, string> = {
  synced: 'badge-success',
  error: 'badge-error',
  skipped: 'badge-warning',
}

const STATUS_LABEL: Record<string, string> = {
  synced: 'Synced',
  error: 'Error',
  skipped: 'Skipped',
}

export default function DataPactSyncPanel({
  assessmentId,
  practiceId,
  syncStatus,
  syncAt,
  onSyncComplete,
}: Props) {
  const [syncing, setSyncing] = useState(false)
  const [result, setResult] = useState<SyncResult | null>(null)
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [showLogs, setShowLogs] = useState(false)

  const loadLogs = useCallback(async () => {
    try {
      const data = await getSyncLogs({ assessment_id: assessmentId, limit: 10 })
      setLogs(data.items.filter((l) => l.practice_id === practiceId))
    } catch {
      // Silently fail for logs
    }
  }, [assessmentId, practiceId])

  useEffect(() => {
    if (showLogs) loadLogs()
  }, [showLogs, loadLogs])

  // Reset result when practice changes
  useEffect(() => {
    setResult(null)
  }, [practiceId])

  async function handleSync() {
    setSyncing(true)
    setResult(null)
    try {
      const res = await syncPractice(assessmentId, practiceId)
      setResult(res)
      onSyncComplete()
      if (showLogs) loadLogs()
    } catch (err) {
      setResult({
        practice_id: practiceId,
        status: 'error',
        message: err instanceof Error ? err.message : 'Sync failed',
        compliance: null,
      })
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="mb-4">
      <h3 className="text-sm font-medium mb-2">DataPact Sync</h3>

      {/* Status row */}
      <div className="flex items-center gap-2 mb-2">
        {syncStatus ? (
          <>
            <span className={`badge badge-sm ${STATUS_BADGE[syncStatus] ?? 'badge-ghost'}`}>
              {STATUS_LABEL[syncStatus] ?? syncStatus}
            </span>
            {syncAt && (
              <span className="text-xs text-base-content/50">
                Last sync: {new Date(syncAt).toLocaleDateString()}
              </span>
            )}
          </>
        ) : (
          <span className="text-xs text-base-content/50 italic">Never synced</span>
        )}
      </div>

      {/* Sync button */}
      <button
        className="btn btn-outline btn-sm"
        onClick={handleSync}
        disabled={syncing}
        aria-label={syncing ? 'Syncing...' : 'Sync This Practice'}
      >
        {syncing ? (
          <>
            <span className="loading loading-spinner loading-xs" />
            Syncing...
          </>
        ) : (
          'Sync This Practice'
        )}
      </button>

      {/* Result feedback */}
      {result && (
        <div
          className={`mt-2 text-sm px-3 py-2 rounded ${
            result.status === 'success' || result.status === 'synced'
              ? 'bg-success/10 text-success'
              : result.status === 'error'
                ? 'bg-error/10 text-error'
                : 'bg-warning/10 text-warning'
          }`}
        >
          {result.message || `Sync ${result.status}`}
        </div>
      )}

      {/* Sync history toggle */}
      <button
        className="btn btn-ghost btn-xs mt-2"
        onClick={() => setShowLogs(!showLogs)}
      >
        {showLogs ? 'Hide' : 'Sync History'}
      </button>

      {/* Sync log table */}
      {showLogs && (
        <div className="mt-2 overflow-x-auto">
          {logs.length === 0 ? (
            <p className="text-xs text-base-content/50 italic">No sync history</p>
          ) : (
            <table className="table table-xs w-full">
              <thead>
                <tr>
                  <th>Practice</th>
                  <th>Status</th>
                  <th>Error</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="font-mono text-xs">{log.practice_id}</td>
                    <td>
                      <span
                        className={`badge badge-xs ${
                          log.status === 'success' ? 'badge-success' : 'badge-error'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="text-xs text-error">{log.error_message ?? '—'}</td>
                    <td className="text-xs">{new Date(log.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
