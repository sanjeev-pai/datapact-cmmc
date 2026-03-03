# Plan: phase7/dashboard-service — Dashboard Data Aggregation

## Overview
Backend service that aggregates assessment, practice, and finding data into dashboard-ready summaries.

## Functions

### `get_compliance_summary(db, org_id) -> dict`
Returns overall compliance % for the org's most recent completed assessment at each target level.
- Query most recent completed assessment per level for org
- For each, calculate met/total ratio
- Return `{level_1: float|None, level_2: float|None, level_3: float|None}`

### `get_domain_compliance(db, assessment_id) -> list[dict]`
Per-domain scores for a specific assessment.
- Join AssessmentPractice → CMMCPractice to group by domain_ref
- For each domain: count met, total (excluding not_applicable), calculate %
- Return `[{domain_id, domain_name, met, total, percentage}, ...]`

### `get_sprs_summary(db, org_id) -> dict`
Current + historical SPRS for the org.
- Query all assessments with non-null sprs_score ordered by created_at
- Return `{current: int|None, history: [{assessment_id, title, sprs_score, date}, ...]}`

### `get_assessment_timeline(db, org_id, limit=10) -> list[dict]`
Recent assessments with status.
- Query assessments ordered by created_at DESC
- Return `[{id, title, status, target_level, assessment_type, overall_score, sprs_score, created_at, completed_at}, ...]`

### `get_findings_summary(db, assessment_id) -> dict`
Counts by severity and status.
- Query findings for the assessment
- Group by severity, then by status within each
- Return `{by_severity: {critical: n, high: n, ...}, by_status: {open: n, closed: n, ...}, total: n}`

## File
`cmmc/services/dashboard_service.py`

## Tests
`tests/test_dashboard_service.py` — seed org, assessments, practices, findings; verify each function.
