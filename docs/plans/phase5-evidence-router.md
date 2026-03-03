# Plan: phase5/evidence-router

## Objective
Expose evidence CRUD + review + download via REST API at `/api/evidence`.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/evidence` | compliance_officer+ | Upload evidence (multipart file + JSON metadata) |
| GET | `/api/evidence` | authenticated | List with filters (assessment_practice_id, assessment_id, review_status) |
| GET | `/api/evidence/{id}` | authenticated | Get single evidence |
| GET | `/api/evidence/{id}/download` | authenticated | Stream file download |
| DELETE | `/api/evidence/{id}` | compliance_officer+ | Delete pending evidence |
| POST | `/api/evidence/{id}/review` | assessor+ | Accept or reject evidence |

## Implementation
- `cmmc/routers/evidence.py` — FastAPI router
- Register in `cmmc/app.py`
- Upload uses `UploadFile` from FastAPI for multipart, plus `Form` fields for metadata
- Download uses `FileResponse` from `starlette.responses`

## Tests (`tests/test_evidence_api.py`)
- Test each endpoint: happy path, auth, validation
- Use same helper pattern as test_assessment_api.py
