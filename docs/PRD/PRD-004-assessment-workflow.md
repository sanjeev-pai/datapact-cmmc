---
id: PRD-004
title: "Assessment Workflow"
description: "CMMC assessment CRUD, status lifecycle, practice evaluation, and scoring"
priority: HIGH
status: IN_PROGRESS
created: 2026-03-03
depends_on: [PRD-002, PRD-003]
---

# Assessment Workflow

## Overview

Organizations perform CMMC assessments to evaluate their compliance posture against CMMC 2.0 practices. This phase introduces assessment CRUD operations, a status lifecycle (draft -> in_progress -> under_review -> completed), practice evaluation, and SPRS scoring.

## Business Capability

### 1. Assessment Management

Users with compliance_officer+ roles can create, update, and delete assessments scoped to their organization. Each assessment targets a CMMC level (1/2/3) and type (self/third_party/government). Creating an assessment auto-populates assessment_practice records for all practices at or below the target level.

### 2. Status Lifecycle

Assessments follow a linear workflow: draft -> in_progress -> under_review -> completed. Invalid transitions are rejected. Timestamps are recorded for start and completion events.

### 3. Practice Evaluation (future sub-phase)

Assessors evaluate individual practices within an in-progress assessment, recording status (met/not_met/partially_met/not_applicable), score, and notes.

### 4. SPRS Scoring (future sub-phase)

Auto-calculated SPRS score (-203 to 110) based on practice evaluation results per NIST 800-171 DoD Assessment Methodology.

## Phases

- **phase4/assessment-schemas** — Pydantic schemas (DONE)
- **phase4/assessment-service** — Business logic (DONE)
- **phase4/assessment-router** — API endpoints (CURRENT)
- **phase4/practice-eval-service** — Practice evaluation logic
- **phase4/practice-eval-router** — Practice evaluation API
- **phase4/sprs-scoring** — SPRS score calculation
- **phase4/ui-assessment-list** — Assessment list page
- **phase4/ui-assessment-create** — Assessment creation form
- **phase4/ui-assessment-workspace** — Assessment workspace
- **phase4/ui-scoring-display** — Scoring widgets

## API Endpoints (phase4/assessment-router)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/assessments | compliance_officer+ | Create assessment |
| GET | /api/assessments | authenticated | List with filters (org_id, status, level) |
| GET | /api/assessments/{id} | authenticated | Get detail |
| PATCH | /api/assessments/{id} | compliance_officer+ | Update fields |
| DELETE | /api/assessments/{id} | compliance_officer+ | Delete draft only |
| POST | /api/assessments/{id}/start | compliance_officer+ | draft -> in_progress |
| POST | /api/assessments/{id}/submit | compliance_officer+ | in_progress -> under_review |
| POST | /api/assessments/{id}/complete | compliance_officer+ | under_review -> completed |

## Authorization Rules

- System admins can access assessments across all organizations
- Other roles are scoped to their own organization
- Viewers can read assessments but cannot create/update/delete or transition status
