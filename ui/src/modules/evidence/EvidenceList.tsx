import type { Evidence, ReviewStatus } from '@/types/evidence'
import { deleteEvidence, getDownloadUrl } from '@/services/evidence'

interface Props {
  items: Evidence[]
  editable: boolean
  onDeleted: (id: string) => void
}

const STATUS_BADGE: Record<ReviewStatus, string> = {
  pending: 'badge-ghost',
  accepted: 'badge-success',
  rejected: 'badge-error',
}

const STATUS_LABEL: Record<ReviewStatus, string> = {
  pending: 'Pending',
  accepted: 'Accepted',
  rejected: 'Rejected',
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function EvidenceList({ items, editable, onDeleted }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-base-content/50 italic">No evidence uploaded yet.</p>
    )
  }

  async function handleDelete(id: string) {
    try {
      await deleteEvidence(id)
      onDeleted(id)
    } catch {
      // silently fail — could show toast in future
    }
  }

  return (
    <ul className="space-y-1.5">
      {items.map((ev) => (
        <li
          key={ev.id}
          className="flex items-center gap-2 text-sm bg-base-200/50 rounded px-2 py-1.5"
        >
          {/* File icon */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-base-content/40 shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
          </svg>

          {/* Title + metadata */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              {ev.file_name ? (
                <a
                  href={getDownloadUrl(ev.id)}
                  className="font-medium truncate hover:underline text-primary"
                  title={ev.file_name}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {ev.title}
                </a>
              ) : (
                <span className="font-medium truncate">{ev.title}</span>
              )}
              <span className={`badge badge-xs ${STATUS_BADGE[ev.review_status]}`}>
                {STATUS_LABEL[ev.review_status]}
              </span>
            </div>
            {ev.file_size && (
              <span className="text-xs text-base-content/40">{formatSize(ev.file_size)}</span>
            )}
          </div>

          {/* Delete button (only for pending + editable) */}
          {editable && ev.review_status === 'pending' && (
            <button
              className="btn btn-ghost btn-xs btn-square text-error"
              onClick={() => handleDelete(ev.id)}
              aria-label={`Delete ${ev.title}`}
              title="Delete"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}
