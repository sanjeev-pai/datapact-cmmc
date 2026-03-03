import { useCallback, useEffect, useState } from 'react'
import type { Evidence } from '@/types/evidence'
import { listEvidence } from '@/services/evidence'
import EvidenceList from './EvidenceList'
import EvidenceUpload from './EvidenceUpload'

interface Props {
  assessmentPracticeId: string
  editable: boolean
}

export default function EvidencePanel({ assessmentPracticeId, editable }: Props) {
  const [items, setItems] = useState<Evidence[]>([])
  const [loading, setLoading] = useState(true)

  const loadEvidence = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listEvidence({ assessment_practice_id: assessmentPracticeId })
      setItems(data.items)
    } catch {
      // fail silently — evidence section is supplementary
    } finally {
      setLoading(false)
    }
  }, [assessmentPracticeId])

  useEffect(() => {
    loadEvidence()
  }, [loadEvidence])

  function handleUploaded(ev: Evidence) {
    setItems((prev) => [ev, ...prev])
  }

  function handleDeleted(id: string) {
    setItems((prev) => prev.filter((e) => e.id !== id))
  }

  return (
    <div className="space-y-3">
      {loading ? (
        <div className="flex justify-center py-2">
          <span className="loading loading-spinner loading-sm" />
        </div>
      ) : (
        <EvidenceList items={items} editable={editable} onDeleted={handleDeleted} />
      )}

      {editable && (
        <EvidenceUpload
          assessmentPracticeId={assessmentPracticeId}
          onUploaded={handleUploaded}
        />
      )}
    </div>
  )
}
