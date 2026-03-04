---
id: PRD-008
title: "POA&M Management"
description: "Plan of Action and Milestones tracking for unresolved findings"
priority: HIGH
status: IN_PROGRESS
created: 2026-03-03
depends_on: [PRD-004, PRD-005]
---

# POA&M Management

## Overview

Organizations undergoing CMMC assessments need to track remediation of findings (deficiencies, observations). A POA&M (Plan of Action and Milestones) documents what needs fixing, who is responsible, target dates, and progress. This phase adds full POA&M lifecycle management including auto-generation from assessment findings.

## Business Capability

### 1. POA&M CRUD

Create, read, update, and delete POA&M plans linked to assessments and organizations. Status lifecycle: draft -> active -> completed.

### 2. POA&M Items

Individual remediation items within a POA&M, each linked to a finding and/or practice. Track milestone, scheduled/actual completion dates, resources required, and risk acceptance.

### 3. Auto-Generation from Findings

Generate POA&M items automatically from unresolved findings in a completed assessment, reducing manual data entry.

### 4. Findings Management

CRUD endpoints for assessment findings (deficiency, observation, recommendation). Findings drive POA&M item creation.

### 5. UI — Findings Page, POA&M List, Detail, and Kanban

Frontend pages for managing findings, viewing POA&M plans in list and kanban views, and editing POA&M items.

## Out of Scope

- Automated email notifications for overdue items
- External POA&M import/export (DoD SPRS format)
- Workflow approval chains for POA&M completion

## Success Metrics

### Quality Metrics

- All CRUD operations covered by tests
- Schema validation prevents invalid status transitions

### Operational Metrics

- Auto-generation creates POA&M items for all unresolved findings

## Dependencies

- PRD-004: Assessment workflow (assessments, findings model)
- PRD-005: Evidence management (evidence linked to practices)

## Implementation Reference

Phases defined in MEMORY.md: phase8/poam-schemas, phase8/poam-service, phase8/poam-router, phase8/finding-router, phase8/ui-findings, phase8/ui-poam-list, phase8/ui-poam-kanban, phase8/ui-poam-detail.
