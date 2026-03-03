import { useRef, useState } from 'react'
import { uploadEvidence } from '@/services/evidence'
import type { Evidence } from '@/types/evidence'

interface Props {
  assessmentPracticeId: string
  onUploaded: (evidence: Evidence) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function EvidenceUpload({ assessmentPracticeId, onUploaded }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) {
      setFile(dropped)
      if (!title) setTitle(dropped.name.replace(/\.[^.]+$/, ''))
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
    if (selected && !title) setTitle(selected.name.replace(/\.[^.]+$/, ''))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return

    setUploading(true)
    setError(null)
    try {
      const ev = await uploadEvidence({
        assessment_practice_id: assessmentPracticeId,
        title: title.trim(),
        description: description.trim() || undefined,
        file: file ?? undefined,
      })
      onUploaded(ev)
      // Reset form
      setTitle('')
      setDescription('')
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {/* Drop zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-3 text-center text-sm cursor-pointer transition-colors ${
          dragOver ? 'border-primary bg-primary/5' : 'border-base-300 hover:border-base-content/30'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        role="button"
        aria-label="Drop file here or click to browse"
      >
        {file ? (
          <div className="flex items-center justify-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-success" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-medium truncate max-w-[200px]">{file.name}</span>
            <span className="text-base-content/50">({formatSize(file.size)})</span>
          </div>
        ) : (
          <span className="text-base-content/50">Drop file here or click to browse</span>
        )}
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
          data-testid="file-input"
        />
      </div>

      {/* Title */}
      <input
        type="text"
        className="input input-bordered input-sm w-full"
        placeholder="Evidence title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
        aria-label="Evidence title"
      />

      {/* Description (optional) */}
      <textarea
        className="textarea textarea-bordered textarea-sm w-full"
        placeholder="Description (optional)"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        aria-label="Evidence description"
      />

      {error && (
        <div className="text-error text-xs">{error}</div>
      )}

      <button
        type="submit"
        className="btn btn-primary btn-sm btn-block"
        disabled={uploading || !title.trim()}
      >
        {uploading ? 'Uploading...' : 'Upload Evidence'}
      </button>
    </form>
  )
}
