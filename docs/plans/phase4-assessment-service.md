---
prd: "PRD-004-assessment-workflow"
title: "Phase 4: Assessment Service"
description: "Business logic for assessment CRUD with status lifecycle and practice population"
status: IN_PROGRESS
created: 2026-03-03
depends_on: [phase4/assessment-schemas]
---

# Phase 4: Assessment Service

**Goal:** Implement assessment business logic with CRUD, status transitions, and auto-population of assessment practices.

**Architecture:** Service functions taking SQLAlchemy Session, returning ORM models. Status lifecycle enforced in service layer.

## Tasks

### Task 1: Assessment CRUD + practice population + status transitions

**Test:**
```text
- create_assessment creates assessment with draft status
- create_assessment populates assessment_practices for all practices at target level
- create_assessment populates practices at target level AND below
- get_assessment returns assessment by ID
- get_assessment raises NotFoundError for missing ID
- list_assessments returns all assessments for an org
- list_assessments filters by status
- list_assessments filters by target_level
- update_assessment updates allowed fields
- update_assessment raises NotFoundError for missing ID
- update_assessment rejects updates on completed assessments
- delete_assessment removes draft assessment
- delete_assessment raises ConflictError for non-draft
- start_assessment transitions draft -> in_progress, sets started_at
- submit_assessment transitions in_progress -> under_review
- complete_assessment transitions under_review -> completed, sets completed_at
- invalid transitions raise ConflictError
```

**Verification:** `uv run pytest tests/test_assessment_service.py -v`

**Commit:** `feat(services): add assessment service with CRUD and status lifecycle (PRD-004)`

## Final Validation

- [ ] All tests pass
- [ ] Status updated in plan
