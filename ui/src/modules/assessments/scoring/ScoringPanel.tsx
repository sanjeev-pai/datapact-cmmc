import { useState } from 'react'
import type { Assessment, AssessmentPractice } from '@/types/assessment'
import type { CMMCDomain, CMMCPractice } from '@/types/cmmc'
import SprsGauge from './SprsGauge'
import ComplianceBar from './ComplianceBar'
import DomainComplianceChart from './DomainComplianceChart'

interface Props {
  assessment: Assessment
  domains: CMMCDomain[]
  practices: CMMCPractice[]
  evaluations: AssessmentPractice[]
}

export default function ScoringPanel({ assessment, domains, practices, evaluations }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="border-b border-base-300 bg-base-100 shrink-0">
      <div className="flex items-center justify-between px-4 py-1">
        <span className="text-xs font-semibold text-base-content/50 uppercase tracking-wide">Scoring</span>
        <button
          className="btn btn-ghost btn-xs btn-square"
          onClick={() => setCollapsed((v) => !v)}
          aria-label="Toggle scoring panel"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-4 w-4 transition-transform ${collapsed ? '' : 'rotate-180'}`}
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      <div
        data-testid="scoring-panel-content"
        className={collapsed ? 'hidden' : ''}
      >
        <div className="grid grid-cols-[auto_1fr_1fr] gap-6 px-4 pb-3 items-start">
          {/* SPRS Gauge */}
          <SprsGauge score={assessment.sprs_score} />

          {/* Overall compliance */}
          <div className="pt-2">
            <ComplianceBar percentage={assessment.overall_score} />
          </div>

          {/* Domain breakdown */}
          <DomainComplianceChart
            domains={domains}
            practices={practices}
            evaluations={evaluations}
          />
        </div>
      </div>
    </div>
  )
}
