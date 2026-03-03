# Phase 6a: DataPact Client — Implementation Plan

## TODO
`phase6/datapact-client` — httpx DataPact API client

## Scope
- `cmmc/services/datapact_client.py` — `DataPactClient` class
- `tests/test_datapact_client.py` — tests using `respx` to mock httpx

## Design

### DataPactClient class
- Constructor: `__init__(base_url, api_key, timeout)` with defaults from config
- Methods:
  - `get_contracts()` → list of contracts
  - `get_contract(contract_id)` → single contract
  - `get_contract_compliance(contract_id)` → compliance data
- Uses `httpx.AsyncClient` internally for non-blocking I/O
- Sends `Authorization: Bearer {api_key}` header
- Custom exceptions: `DataPactConnectionError`, `DataPactAuthError`, `DataPactNotFoundError`, `DataPactRateLimitError`, `DataPactError`

### Error Handling
- `httpx.TimeoutException` → `DataPactConnectionError`
- `httpx.ConnectError` → `DataPactConnectionError`
- 401/403 → `DataPactAuthError`
- 404 → `DataPactNotFoundError`
- 429 → `DataPactRateLimitError`
- 5xx → `DataPactError`

### Testing
- Use `respx` library to mock httpx requests
- Test each method with success and error scenarios
- Test timeout handling
- Test auth header sent correctly

## Files
| File | Change |
|------|--------|
| `cmmc/services/datapact_client.py` | New — client class |
| `tests/test_datapact_client.py` | New — tests |
| `docs/PRD/PRD-006-datapact-integration.md` | New — PRD |
