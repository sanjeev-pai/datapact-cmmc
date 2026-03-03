---
id: PRD-005
title: "Evidence Management"
description: "Upload, review, and manage evidence artifacts linked to assessment practice evaluations"
priority: HIGH
status: IN_PROGRESS
created: 2026-03-03
depends_on: [PRD-004]
---

# Evidence Management

## Overview

Assessors attach evidence artifacts (documents, screenshots, policy files) to individual practice evaluations within an assessment. Evidence goes through a review workflow (pending → accepted/rejected) and can be filtered by assessment, practice, or review status.

## Business Capability

### 1. Evidence Upload
Users upload files with a title and optional description, linked to a specific assessment_practice. Files are stored on the local filesystem under `uploads/`. A DB record tracks metadata (filename, size, MIME type, path).

### 2. Evidence Review
Assessors or reviewers can accept or reject evidence. Review actions record the reviewer and timestamp.

### 3. Evidence Browsing
List evidence filtered by assessment, practice, or review status. Download files via streaming endpoint.

## Phases

- **phase5/evidence-schemas** — Pydantic request/response schemas (CURRENT)
- **phase5/evidence-service** — Business logic (upload, list, review, delete)
- **phase5/evidence-router** — API endpoints
- **phase5/ui-evidence-upload** — Upload component in workspace
- **phase5/ui-evidence-list** — Evidence list & review UI

## Data Model

See `cmmc/models/evidence.py` — Evidence table with:
- assessment_practice_id (FK)
- title, description
- file_path, file_url
- review_status (pending/accepted/rejected)
- reviewer_id (FK), reviewed_at
