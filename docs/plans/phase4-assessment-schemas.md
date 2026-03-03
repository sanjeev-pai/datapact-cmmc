---
prd: "PRD-004-assessment-workflow"
title: "Phase 4: Assessment Pydantic Schemas"
description: "Request/response schemas for assessment CRUD and practice evaluation"
status: IN_PROGRESS
created: 2026-03-03
depends_on: [phase2/models-migration]
---

# Phase 4: Assessment Pydantic Schemas

**Goal:** Create Pydantic schemas for assessment CRUD and practice evaluation with status enum validation.

**Architecture:** Pydantic v2 models with `from_attributes` config, Field constraints, and Literal types for enums.

**Tech Stack:** Pydantic v2, Python typing (Literal).

## Tasks

### Task 1: Assessment schemas

**Test:**
```text
- AssessmentCreate validates required fields (org_id, title, target_level)
- AssessmentCreate rejects invalid target_level (0, 4)
- AssessmentCreate rejects invalid assessment_type
- AssessmentUpdate allows partial updates (all fields optional)
- AssessmentResponse serializes all fields including timestamps
- AssessmentListResponse wraps list of assessments with count
```

**Implementation:**
1. Create `cmmc/schemas/assessment.py` with:
   - Status/type Literal types
   - AssessmentCreate, AssessmentUpdate
   - AssessmentResponse, AssessmentListResponse
   - AssessmentPracticeResponse, AssessmentPracticeUpdate

**Verification:** `uv run pytest tests/test_assessment_schemas.py -v`

**Commit:** `feat(schemas): add assessment and practice evaluation Pydantic schemas (PRD-004)`

## Final Validation

- [ ] All schema tests pass
- [ ] Status updated in plan
