import type { CMMCDomain, CMMCPractice } from '@/types/cmmc'
import type { AssessmentPractice } from '@/types/assessment'

interface Props {
  domains: CMMCDomain[]
  practices: CMMCPractice[]
  evaluations: AssessmentPractice[]
}

interface DomainStat {
  name: string
  domainId: string
  total: number
  met: number
  percentage: number
}

function computeDomainStats(
  domains: CMMCDomain[],
  practices: CMMCPractice[],
  evaluations: AssessmentPractice[],
): DomainStat[] {
  const evalMap = new Map<string, AssessmentPractice>()
  for (const ev of evaluations) {
    evalMap.set(ev.practice_id, ev)
  }

  const practicesByDomain = new Map<string, CMMCPractice[]>()
  for (const p of practices) {
    const list = practicesByDomain.get(p.domain_ref) || []
    list.push(p)
    practicesByDomain.set(p.domain_ref, list)
  }

  return domains
    .filter((d) => practicesByDomain.has(d.domain_id))
    .map((d) => {
      const domainPractices = practicesByDomain.get(d.domain_id) || []
      // Exclude not_applicable from total
      const applicable = domainPractices.filter((p) => {
        const ev = evalMap.get(p.practice_id)
        return ev?.status !== 'not_applicable'
      })
      const met = applicable.filter((p) => {
        const ev = evalMap.get(p.practice_id)
        return ev?.status === 'met'
      })
      const total = applicable.length
      const percentage = total > 0 ? Math.round((met.length / total) * 100) : 0
      return {
        name: d.name,
        domainId: d.domain_id,
        total,
        met: met.length,
        percentage,
      }
    })
}

function getBarColor(pct: number): string {
  if (pct < 34) return 'bg-error'
  if (pct < 67) return 'bg-warning'
  return 'bg-success'
}

export default function DomainComplianceChart({ domains, practices, evaluations }: Props) {
  const stats = computeDomainStats(domains, practices, evaluations)

  if (stats.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        <span className="text-xs text-base-content/60">Domain Compliance</span>
        <span className="text-sm text-base-content/40">No domain data</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-base-content/60">Domain Compliance</span>
      <div className="flex flex-col gap-1.5">
        {stats.map((s) => (
          <div key={s.domainId} className="flex items-center gap-2">
            <span className="text-xs w-28 truncate text-base-content/70" title={s.name}>
              {s.name}
            </span>
            <div className="flex-1 h-2 bg-base-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${getBarColor(s.percentage)}`}
                style={{ width: `${s.percentage}%` }}
              />
            </div>
            <span className="text-xs tabular-nums w-8 text-right font-medium">{s.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
