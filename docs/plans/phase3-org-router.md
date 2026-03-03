# Phase 3: Organization Router — Implementation Plan

**TODO**: `phase3/org-router`
**Branch**: `todo/phase3-org-router`
**PRD**: PRD-003 (Auth & RBAC)

## Scope

Organization CRUD endpoints at `/api/organizations` with role-based access control.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/organizations` | system_admin | Create organization |
| GET | `/api/organizations` | authenticated | List organizations (system_admin: all, others: own org) |
| GET | `/api/organizations/{id}` | authenticated | Get organization detail (system_admin: any, others: own org) |
| PATCH | `/api/organizations/{id}` | system_admin or org_admin (own org) | Update organization |
| DELETE | `/api/organizations/{id}` | system_admin | Delete organization |

## Files

### New
- `cmmc/schemas/organization.py` — Pydantic request/response models
- `cmmc/routers/organizations.py` — FastAPI router
- `tests/test_org_api.py` — API tests

### Modified
- `cmmc/app.py` — Register organization router

## Schemas

- `OrganizationCreate(name, cage_code?, duns_number?, target_level?)`
- `OrganizationUpdate(name?, cage_code?, duns_number?, target_level?)`
- `OrganizationResponse(id, name, cage_code, duns_number, target_level, created_at, updated_at)`

## Authorization Logic

- **POST /**: `require_role("system_admin")`
- **GET /**: `get_current_user` — system_admin sees all orgs, others see only their own org
- **GET /{id}**: `get_current_user` — system_admin can view any, others only their own org
- **PATCH /{id}**: `get_current_user` — system_admin can update any, org_admin can update own org
- **DELETE /{id}**: `require_role("system_admin")`

## Test Cases

- POST: success (system_admin), forbidden (non-admin), duplicate name check, validation
- GET list: system_admin sees all, regular user sees own org only, unauthenticated 401
- GET detail: success, not found, forbidden (wrong org)
- PATCH: success (system_admin), success (org_admin own org), forbidden (org_admin other org), not found
- DELETE: success, forbidden (non-admin), not found
