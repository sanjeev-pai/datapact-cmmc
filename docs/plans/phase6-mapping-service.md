# Phase 6b: Mapping Service — Implementation Plan

## TODO
`phase6/mapping-service` — Practice-to-contract mapping service

## Scope
- `cmmc/services/mapping_service.py` — CRUD + auto-suggest for practice↔contract mappings
- `tests/test_mapping_service.py` — tests using SQLite in-memory DB

## Design

### Functions
- `create_mapping(db, org_id, practice_id, datapact_contract_id, datapact_contract_name)` → DataPactPracticeMapping
  - Validates org and practice exist, prevents duplicate (org+practice+contract)
- `get_mappings(db, org_id, practice_id?, datapact_contract_id?)` → list[DataPactPracticeMapping]
  - Filter by org (required), optionally by practice or contract
- `delete_mapping(db, mapping_id)` → None
  - Raises NotFoundError if not found
- `suggest_mappings(db, org_id, contracts)` → list[dict]
  - Takes list of contracts (from DataPact API), matches domain keywords to contract metadata
  - Returns suggestions: `[{practice_id, contract_id, contract_name, reason}]`

### Model Used
- `DataPactPracticeMapping` from `cmmc/models/datapact.py`

## Files
| File | Change |
|------|--------|
| `cmmc/services/mapping_service.py` | New — service |
| `tests/test_mapping_service.py` | New — tests |
