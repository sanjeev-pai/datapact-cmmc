# PRD-009: End-to-End Test Suite

## Overview
Comprehensive backend e2e test suite that validates the full CMMC compliance workflow through the API, from user registration through POA&M generation.

## Goals
- Validate the complete user journey through the API layer
- Catch integration issues between services/routers that unit tests miss
- Serve as living documentation of the expected workflow

## Scope
Backend only — uses FastAPI TestClient against SQLite. No browser/Playwright tests.

## Test Workflows

### 1. Full Assessment Lifecycle
Register → Login → Create Org → Create Assessment → Start → Evaluate Practices → Upload Evidence → Submit → Complete

### 2. Findings & POA&M Flow
Create Findings from completed assessment → Auto-generate POA&M → Manage POA&M items → Activate → Complete

### 3. Dashboard & Reporting
Verify dashboard endpoints return correct aggregated data after assessment completion. Verify report generation.

### 4. Cross-Cutting Concerns
- Auth token flow (access + refresh)
- Role-based access restrictions
- Org scoping (users can't access other orgs' data)
- Status transition enforcement

## Out of Scope
- Frontend e2e (Playwright/Cypress)
- DataPact sync (requires external service)
- Performance/load testing
