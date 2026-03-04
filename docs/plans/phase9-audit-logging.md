# Plan: phase9/audit-logging

## Goal
Implement audit logging to track all write operations (POST/PUT/PATCH/DELETE) with user, action, resource, and IP information.

## Changes

### Middleware (`cmmc/middleware/audit.py`)
- `AuditMiddleware` (BaseHTTPMiddleware): intercepts write requests on `/api/` paths
- Only logs successful responses (2xx)
- Extracts user_id from JWT (no DB lookup)
- Derives resource_type and resource_id from URL path
- Stores method, path, status_code, query in details JSON
- Skips `/api/health` and `/api/auth/refresh`

### Router (`cmmc/routers/audit.py`)
- `GET /api/audit-log` — list audit logs with filters (user_id, action, resource_type), pagination (limit/offset). Admin only.
- `GET /api/audit-log/{id}` — get single log entry. Admin only.

### Schema (`cmmc/schemas/audit.py`)
- `AuditLogResponse` and `AuditLogListResponse` Pydantic models

### Model (pre-existing)
- `cmmc/models/audit.py` — `AuditLog` model already existed with user_id, action, resource_type, resource_id, details (JSON), ip_address

### Tests (`tests/test_audit.py`)
- 4 middleware helper unit tests (resource extraction, action mapping)
- 4 middleware integration tests (POST creates log, GET skipped, failures skipped, user_id captured)
- 7 router tests (admin list, non-admin 403, filters, single get, 404, pagination)
