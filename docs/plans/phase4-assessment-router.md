---
id: phase4-assessment-router
prd: PRD-004
title: "Assessment CRUD API Router"
status: IN_PROGRESS
created: 2026-03-03
---

# Assessment Router Implementation Plan

## Goal

Create `cmmc/routers/assessments.py` with 8 auth-protected endpoints for assessment CRUD and status lifecycle transitions.

## Dependencies

- assessment_service.py (DONE) — business logic
- assessment schemas (DONE) — Pydantic models
- auth dependencies (DONE) — get_current_user, require_role

## Implementation Steps

1. **Write tests** (`tests/test_assessment_api.py`)
   - Follow `test_org_api.py` pattern with helpers
   - Test classes: CreateAssessment, ListAssessments, GetAssessment, UpdateAssessment, DeleteAssessment, StartAssessment, SubmitAssessment, CompleteAssessment
   - Cover: success, auth (forbidden/unauthenticated), validation, org scoping, not found

2. **Write router** (`cmmc/routers/assessments.py`)
   - 8 endpoints delegating to assessment_service
   - Org-scoping: system_admin sees all, others scoped to own org
   - Role gating: compliance_officer+ for write operations, any authenticated for reads

3. **Register router** in `cmmc/app.py`

4. **Create PRD & plan docs**

## Files Changed

- `cmmc/routers/assessments.py` (NEW)
- `cmmc/app.py` (add router import + include)
- `tests/test_assessment_api.py` (NEW)
- `docs/PRD/PRD-004-assessment-workflow.md` (NEW)
- `docs/plans/phase4-assessment-router.md` (NEW)
