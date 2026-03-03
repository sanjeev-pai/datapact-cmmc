---
prd: "PRD-003-auth-rbac"
title: "Phase 3: Auth Dependencies"
description: "FastAPI auth dependencies for JWT extraction, role checking, and permission enforcement"
status: OPEN
created: 2026-03-03
depends_on: [phase3/auth-service]
---

# Phase 3: Auth Dependencies

**Goal:** Provide reusable FastAPI `Depends()` functions that extract the current user from JWT tokens, enforce role requirements, and enable fine-grained permission checks.

**Architecture:** Three dependency layers — `get_current_user` (JWT → User), `require_role` (role gate factory), `PermissionChecker` (fine-grained callable class).

**Tech Stack:** FastAPI Depends, SQLAlchemy, existing auth_service (decode_token), existing error classes.

## Tasks

### Task 1: Write tests (test-first)

**Test:**
```text
tests/test_auth_deps.py — test get_current_user, require_role, PermissionChecker
via TestClient with auth headers
```

**Implementation:**
1. Create `tests/test_auth_deps.py`
2. Add helper fixtures: create test user with roles, generate valid/invalid tokens
3. Test cases for get_current_user: valid token → user, missing header → 401, invalid token → 401, inactive user → 401, non-existent user → 401
4. Test cases for require_role: user with required role → pass, user without → 403, multiple roles (any match) → pass
5. Test cases for PermissionChecker: org-scoped check, role + condition check

**Verification:** `uv run pytest tests/test_auth_deps.py -v`

**Commit:** `test(auth): add auth dependency tests`

---

### Task 2: Implement auth dependencies

**Test:**
```text
All tests from Task 1 should pass
```

**Implementation:**
1. Create `cmmc/dependencies/auth.py`
2. Implement `get_current_user(token, db)` — extract Bearer token from Authorization header, decode with auth_service.decode_token, query User by id, verify active, return User
3. Implement `require_role(*roles)` — dependency factory returning a function that checks user has at least one role
4. Implement `PermissionChecker` — callable class for fine-grained checks (role + org scope)

**Verification:** `uv run pytest tests/test_auth_deps.py -v`

**Commit:** `feat(auth): add FastAPI auth dependencies for JWT and RBAC (PRD-003)`

## Final Validation

- [ ] All tests pass
- [ ] PRD updated
- [ ] MEMORY.md TODO marked complete
