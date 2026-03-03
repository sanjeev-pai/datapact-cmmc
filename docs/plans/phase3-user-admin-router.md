# Plan: phase3/user-admin-router

## Scope
User management CRUD endpoints for org_admin+ roles, following the same patterns as the organizations router.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/users | org_admin+ | List users (scoped to own org; system_admin sees all) |
| GET | /api/users/{id} | org_admin+ | Get user detail |
| PATCH | /api/users/{id} | org_admin+ | Update user (username, email, is_active, org_id, roles) |
| DELETE | /api/users/{id} | org_admin+ | Deactivate user (soft delete — sets is_active=false) |

## Files

### New
- `cmmc/schemas/user.py` — `UserAdminResponse`, `UserAdminUpdate`, `UserListResponse`
- `cmmc/routers/users.py` — Router with CRUD endpoints
- `tests/test_user_api.py` — Test suite

### Modified
- `cmmc/app.py` — Register users router

## Access Control Rules
- **system_admin**: Full access to all users across all orgs. Can assign any role, change org_id.
- **org_admin**: Can manage users within their own org only. Cannot assign system_admin role. Cannot change org_id.
- **Others**: 403 Forbidden on all endpoints.
- A user cannot deactivate themselves.
- org_admin cannot remove their own org_admin role.

## Implementation Steps
1. Write tests (test-first)
2. Create schemas (`cmmc/schemas/user.py`)
3. Create router (`cmmc/routers/users.py`)
4. Register router in `cmmc/app.py`
5. Verify tests pass
