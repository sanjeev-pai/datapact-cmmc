# Phase 6e: UI DataPact Settings — Implementation Plan

## TODO
`phase6/ui-datapact-settings` — DataPact settings page

## Scope
- `ui/src/modules/datapact/DataPactSettingsPage.tsx` — settings form + connection test
- `ui/src/services/datapact.ts` — frontend API client for DataPact endpoints
- `ui/src/types/datapact.ts` — TypeScript types for DataPact entities
- Backend: extend `OrganizationUpdate`/`OrganizationResponse` with datapact fields
- Route at `/datapact`, nav item in sidebar

## Files
| File | Change |
|------|--------|
| `ui/src/modules/datapact/DataPactSettingsPage.tsx` | New — settings page |
| `ui/src/modules/datapact/DataPactSettingsPage.test.tsx` | New — tests |
| `ui/src/services/datapact.ts` | New — API client |
| `ui/src/types/datapact.ts` | New — types |
| `cmmc/schemas/organization.py` | Add datapact fields |
| `cmmc/routers/organizations.py` | Handle datapact fields in PATCH |
| `ui/src/App.tsx` | Add /datapact route |
| `ui/src/components/AppLayout.tsx` | Add DataPact nav item |
