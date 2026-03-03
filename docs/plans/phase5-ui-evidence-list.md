# Phase 5: UI Evidence List — Implementation Plan

## TODO
`phase5/ui-evidence-list` — Evidence list & review UI

## Scope
- `ui/src/modules/evidence/EvidenceListPage.tsx` — standalone page listing all evidence across assessments
- Filters: assessment (dropdown), review status (dropdown)
- Review actions: accept/reject for assessor-level roles
- File download links, status badges (pending/accepted/rejected)
- Nav item in AppLayout sidebar
- Route at `/evidence` in App.tsx
- Evidence seed data in seed_service.py for demo
- Frontend tests for EvidenceListPage

## Files Changed
| File | Change |
|------|--------|
| `ui/src/modules/evidence/EvidenceListPage.tsx` | New — page component |
| `ui/src/modules/evidence/EvidenceListPage.test.tsx` | New — tests |
| `ui/src/App.tsx` | Add `/evidence` route |
| `ui/src/components/AppLayout.tsx` | Add Evidence nav item |
| `cmmc/services/seed_service.py` | Add evidence seed data |

## Implementation Steps
1. Create `EvidenceListPage.tsx` with table, filters, review actions, download links
2. Add route in `App.tsx` and nav item in `AppLayout.tsx`
3. Add evidence seed data in `seed_service.py`
4. Write `EvidenceListPage.test.tsx` covering: renders, loading, empty state, error state, filters, review actions, delete
