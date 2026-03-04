# Plan: phase9/demo-assessment-seed

## Goal
Populate `data/cmmc/demo_assessment.yaml` with realistic demo data (practice evaluations, findings, POAMs) for the existing seed assessments, and update the seed service to optionally load this data.

## Scope

### YAML Data (`data/cmmc/demo_assessment.yaml`)
- **Practice evaluations**: Mixed statuses for 2 assessments:
  - "Acme L1 Self-Assessment (FY25)" (in_progress, L1) — ~60% met, some partially_met, some not_met, some not_evaluated
  - "Pinnacle L2 Self-Assessment (FY25)" (completed, L2) — ~85% met, all evaluated
- **Findings**: 6-8 findings linked to not_met/partially_met practices
- **POAMs**: 2 POAMs (one active, one draft) with 4-6 items each, some overdue

### Seed Service Changes (`cmmc/services/seed_service.py`)
- New functions: `_seed_practice_evaluations()`, `_seed_findings()`, `_seed_poams()`
- New config: `CMMC_SEED_DEMO` (default: true) — controls whether demo data is loaded
- Load YAML from `demo_assessment.yaml`
- Wire into `seed_all()` after evidence seeding

### Config Change (`cmmc/config.py`)
- Add `SEED_DEMO` env var (default: true)

### Tests (`tests/test_seed.py`)
- Verify practice evaluation counts and statuses
- Verify finding counts
- Verify POAM + item counts
- Verify idempotency with demo data
- Verify demo data skipped when `CMMC_SEED_DEMO=false`

## Non-Goals
- No UI changes
- No new API endpoints
- No migration changes (existing models are sufficient)
