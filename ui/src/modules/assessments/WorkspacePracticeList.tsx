import type { CMMCDomain, CMMCPractice } from '@/types/cmmc'
import type { AssessmentPractice, PracticeStatus } from '@/types/assessment'

interface Props {
  domains: CMMCDomain[]
  practices: CMMCPractice[]
  evaluations: AssessmentPractice[]
  selectedPracticeId: string | null
  onSelectPractice: (practiceId: string) => void
}

const STATUS_DOT: Record<PracticeStatus, string> = {
  not_evaluated: 'bg-base-300',
  met: 'bg-success',
  not_met: 'bg-error',
  partially_met: 'bg-warning',
  not_applicable: 'bg-base-300/50',
}

export default function WorkspacePracticeList({
  domains,
  practices,
  evaluations,
  selectedPracticeId,
  onSelectPractice,
}: Props) {
  // Build evaluation lookup by practice_id
  const evalMap = new Map<string, AssessmentPractice>()
  for (const ev of evaluations) {
    evalMap.set(ev.practice_id, ev)
  }

  // Group practices by domain_ref
  const practicesByDomain = new Map<string, CMMCPractice[]>()
  for (const p of practices) {
    const list = practicesByDomain.get(p.domain_ref) || []
    list.push(p)
    practicesByDomain.set(p.domain_ref, list)
  }

  // Only show domains that have practices
  const activeDomains = domains.filter((d) => practicesByDomain.has(d.domain_id))

  return (
    <div className="w-80 min-w-[20rem] border-r border-base-300 overflow-y-auto bg-base-100">
      <div className="p-3 border-b border-base-300">
        <h2 className="text-sm font-semibold text-base-content/70">Practices</h2>
      </div>
      {activeDomains.map((domain) => {
        const domainPractices = practicesByDomain.get(domain.domain_id) || []
        return (
          <div key={domain.domain_id} className="collapse collapse-arrow border-b border-base-200">
            <input type="checkbox" defaultChecked />
            <div className="collapse-title text-sm font-medium py-2 min-h-0">
              {domain.name}
              <span className="text-base-content/50 ml-1">({domainPractices.length})</span>
            </div>
            <div className="collapse-content !pb-1 !pt-0">
              {domainPractices.map((practice) => {
                const ev = evalMap.get(practice.practice_id)
                const status: PracticeStatus = (ev?.status as PracticeStatus) ?? 'not_evaluated'
                const isSelected = selectedPracticeId === practice.practice_id
                return (
                  <button
                    key={practice.practice_id}
                    className={`flex items-center gap-2 w-full text-left px-2 py-1.5 rounded text-sm hover:bg-base-200 transition-colors ${
                      isSelected ? 'bg-primary/10 text-primary font-medium' : ''
                    }`}
                    onClick={() => onSelectPractice(practice.practice_id)}
                  >
                    <span
                      className={`w-2.5 h-2.5 rounded-full shrink-0 ${STATUS_DOT[status]}`}
                      title={status.replace('_', ' ')}
                    />
                    <span className="font-mono text-xs text-base-content/60">{practice.practice_id}</span>
                    <span className="truncate">{practice.title}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
