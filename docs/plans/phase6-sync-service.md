# Phase 6c: Sync Service — Implementation Plan

## TODO
`phase6/sync-service` — DataPact sync service

## Scope
- `cmmc/services/sync_service.py` — sync assessment practices with DataPact compliance data
- `tests/test_sync_service.py` — tests with mocked DataPactClient

## Design

### Functions
- `sync_practice(db, assessment_id, practice_id, client?)` → SyncResult
  - Find the assessment practice + its mapped contract(s)
  - Call `DataPactClient.get_contract_compliance(contract_id)` for each mapping
  - Update `assessment_practice.datapact_sync_status` and `datapact_sync_at`
  - Log to `DataPactSyncLog` (success or error)
  - Returns a result dict with status and any error

- `sync_assessment(db, assessment_id, client?)` → list[SyncResult]
  - Get all assessment practices with mappings
  - Call `sync_practice()` for each
  - Handle partial failures: one practice failing doesn't stop others
  - Returns list of results (some may be errors)

### Client Resolution
- Look up `Organization.datapact_api_url` / `datapact_api_key` for the assessment's org
- Fall back to global config defaults if org fields are null
- Accept optional `client` parameter for testing

### Error Handling
- DataPact errors (auth, timeout, rate limit) → logged as error, practice marked `"error"`
- Missing mapping → skip practice (no sync needed)
- Partial failure → continue syncing remaining practices

## Files
| File | Change |
|------|--------|
| `cmmc/services/sync_service.py` | New — service |
| `tests/test_sync_service.py` | New — tests |
