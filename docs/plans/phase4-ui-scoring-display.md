# Plan: phase4/ui-scoring-display

## Objective
Add scoring visualization widgets to the assessment workspace: SPRS gauge, compliance percentage bar, and domain-level compliance breakdown.

## Components

### 1. `SprsGauge` — Radial gauge for SPRS score
- Range: -203 to 110
- Color zones: red (<-50), orange (-50 to 0), yellow (1-54), green (55+)
- Shows numeric value in center
- Uses Recharts RadialBarChart

### 2. `ComplianceBar` — Horizontal progress bar for overall compliance
- Range: 0-100%
- Color: red (<34), orange (34-66), green (67+)
- Pure CSS (no charting library needed)

### 3. `DomainComplianceChart` — Horizontal bar chart per domain
- Groups evaluations by domain
- Calculates % met per domain
- Color-coded bars using Recharts BarChart

### 4. `ScoringPanel` — Collapsible summary panel
- Positioned between header and body in workspace
- Contains all three widgets in a responsive grid
- Collapsible to avoid taking too much space

## Integration
- Update `AssessmentWorkspacePage.tsx` to replace plain text scores with `ScoringPanel`
- Pass assessment, evaluations, domains, and practices as props

## Tests
- `SprsGauge.test.tsx` — renders score, handles null
- `ComplianceBar.test.tsx` — renders percentage, color zones
- `DomainComplianceChart.test.tsx` — renders domain bars
- `ScoringPanel.test.tsx` — toggle collapse, integrates children

## Files Changed
- NEW: `ui/src/modules/assessments/scoring/SprsGauge.tsx`
- NEW: `ui/src/modules/assessments/scoring/ComplianceBar.tsx`
- NEW: `ui/src/modules/assessments/scoring/DomainComplianceChart.tsx`
- NEW: `ui/src/modules/assessments/scoring/ScoringPanel.tsx`
- NEW: `ui/src/modules/assessments/scoring/__tests__/SprsGauge.test.tsx`
- NEW: `ui/src/modules/assessments/scoring/__tests__/ComplianceBar.test.tsx`
- NEW: `ui/src/modules/assessments/scoring/__tests__/DomainComplianceChart.test.tsx`
- NEW: `ui/src/modules/assessments/scoring/__tests__/ScoringPanel.test.tsx`
- EDIT: `ui/src/modules/assessments/AssessmentWorkspacePage.tsx`
