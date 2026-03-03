# PRD-006: DataPact Integration

## Overview
Integrate the CMMC tracker with DataPact's contract management platform to pull contract compliance data and correlate it with CMMC practice evaluations.

## Goals
- Enable organizations to connect their DataPact instance via API URL + key
- Map CMMC practices to DataPact contracts
- Sync compliance data from DataPact into assessment practice evaluations
- Provide visibility into DataPact sync status and history

## Components

### Phase 6a: DataPact Client (`phase6/datapact-client`)
HTTP client wrapping DataPact's REST API using httpx:
- `get_contracts()` — list contracts for the org
- `get_contract(id)` — get a single contract
- `get_contract_compliance(id)` — get compliance status for a contract
- Configurable base URL, timeout, API key (from org settings or global config)
- Error handling: timeouts, auth failures (401/403), rate limits (429), server errors (5xx)

### Phase 6b: Mapping Service (`phase6/mapping-service`)
Service to manage practice-to-contract mappings.

### Phase 6c: Sync Service (`phase6/sync-service`)
Service to sync DataPact data into assessment practices.

### Phase 6d–f: API Router & UI
Router, settings UI, mapping UI, sync UI.

## API Contract (DataPact)
Expected DataPact API shape (external service):
- `GET /api/contracts` → `{ items: Contract[], total: int }`
- `GET /api/contracts/{id}` → `Contract`
- `GET /api/contracts/{id}/compliance` → `{ contract_id, status, score, details }`

Where `Contract` = `{ id, title, description, status, parties, created_at, updated_at }`

## Configuration
- Global defaults: `DATAPACT_API_URL`, `DATAPACT_TIMEOUT` in `cmmc/config.py`
- Per-org overrides: `organizations.datapact_api_url`, `organizations.datapact_api_key`
