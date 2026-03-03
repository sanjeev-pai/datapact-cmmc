# Phase 6d: DataPact Router — Implementation Plan

## TODO
`phase6/datapact-router` — DataPact API endpoints

## Scope
- `cmmc/schemas/datapact.py` — Pydantic request/response schemas
- `cmmc/routers/datapact.py` — API router with prefix `/api/datapact`
- `tests/test_datapact_api.py` — API tests
- `cmmc/app.py` — register router

## Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/datapact/contracts` | Proxy to DataPact: list contracts |
| GET | `/api/datapact/mappings` | List mappings for user's org |
| POST | `/api/datapact/mappings` | Create a practice-to-contract mapping |
| DELETE | `/api/datapact/mappings/{id}` | Delete a mapping |
| POST | `/api/datapact/sync/{assessment_id}` | Trigger full assessment sync |
| POST | `/api/datapact/sync/{assessment_id}/{practice_id}` | Sync single practice |
| GET | `/api/datapact/sync-logs` | Recent sync history |

## Auth
- All endpoints require authentication (`get_current_user`)
- Write operations (POST/DELETE) require `compliance_officer` or higher

## Files
| File | Change |
|------|--------|
| `cmmc/schemas/datapact.py` | New — schemas |
| `cmmc/routers/datapact.py` | New — router |
| `tests/test_datapact_api.py` | New — tests |
| `cmmc/app.py` | Add router import + include |
