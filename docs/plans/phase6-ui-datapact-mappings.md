# Phase 6: UI DataPact Mappings — Implementation Plan

## Overview
Practice-to-contract mapping UI page for the DataPact integration module.

## Scope
- Backend: Add `POST /api/datapact/suggest` endpoint to expose auto-suggest service
- Frontend: `DataPactMappingsPage` with mapping table, add/remove, auto-suggest, domain filter
- Frontend: Tab navigation between Settings and Mappings pages
- Frontend: Admin users (system_admin) can access DataPact pages without org membership
- Tests: Backend test for suggest endpoint, frontend vitest tests for mappings page

## Files Changed

### Backend
- `cmmc/routers/datapact.py` — add suggest endpoint
- `tests/test_datapact_api.py` — add suggest tests

### Frontend
- `ui/src/types/datapact.ts` — add `MappingSuggestion` type
- `ui/src/services/datapact.ts` — add `suggestMappings()` function
- `ui/src/modules/datapact/DataPactMappingsPage.tsx` — new page component
- `ui/src/modules/datapact/DataPactMappingsPage.test.tsx` — tests
- `ui/src/modules/datapact/DataPactNav.tsx` — shared tab navigation
- `ui/src/modules/datapact/DataPactSettingsPage.tsx` — add nav, admin org selector
- `ui/src/modules/datapact/DataPactSettingsPage.test.tsx` — update title expectation
- `ui/src/App.tsx` — add `/datapact/mappings` route

## Testing
- `make test-backend` for suggest endpoint tests
- `make test-frontend` for mappings page tests
