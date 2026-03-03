---
prd: "PRD-003-auth-rbac"
title: "Phase 3: Auth Router"
description: "Auth API endpoints for registration, login, token refresh, and profile management"
status: OPEN
created: 2026-03-03
depends_on: [phase3/auth-service, phase3/auth-dependencies]
---

# Phase 3: Auth Router

**Goal:** Provide REST API endpoints for user registration, login (JWT issuance), token refresh, and profile retrieval/update.

**Architecture:** FastAPI router at `/api/auth` using Pydantic request/response schemas. Registration creates user + assigns default `viewer` role. Login verifies credentials and returns access + refresh tokens. Token refresh validates refresh token and issues new access token. Profile endpoints use `get_current_user` dependency.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, existing auth_service + auth dependencies.

## Tasks

### Task 1: Create Pydantic schemas

**Implementation:**
1. `cmmc/schemas/auth.py`: `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `UserUpdateRequest`

### Task 2: Write tests (test-first)

**Implementation:**
1. `tests/test_auth_api.py`: tests for all 5 endpoints via TestClient
2. Register: success, duplicate username, duplicate email, weak password
3. Login: success, wrong password, nonexistent user, inactive user
4. Refresh: valid refresh token, expired token, access token rejected
5. GET /me: authenticated, unauthenticated
6. PATCH /me: update email, update username, no-op

### Task 3: Implement auth router

**Implementation:**
1. `cmmc/routers/auth.py`: router with prefix `/api/auth`
2. Wire router into `cmmc/app.py`
3. All 5 endpoints: register, login, refresh, me (GET), me (PATCH)

**Verification:** `uv run pytest tests/test_auth_api.py -v`

**Commit:** `feat(auth): add auth API endpoints for register, login, refresh, profile (PRD-003)`

## Final Validation

- [ ] All tests pass
- [ ] Full suite passes (no regressions)
- [ ] MEMORY.md TODO marked complete
