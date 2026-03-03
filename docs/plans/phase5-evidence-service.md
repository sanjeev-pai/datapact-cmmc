# Plan: phase5/evidence-service

## Objective
Implement evidence business logic: upload, get, list, delete, review. File storage to configurable uploads/ directory.

## Config Changes
Add to `cmmc/config.py`:
- `UPLOAD_DIR` — default `uploads/` (relative to project root)
- `MAX_UPLOAD_SIZE` — default 50MB

## Service Functions (`cmmc/services/evidence_service.py`)

### `upload_evidence(db, *, assessment_practice_id, title, description, file_content, file_name, mime_type) -> Evidence`
- Validate assessment_practice exists
- Save file to `{UPLOAD_DIR}/{evidence_id}/{file_name}`
- Create DB record with file metadata
- Return Evidence

### `get_evidence(db, evidence_id) -> Evidence`
- Lookup by ID, raise NotFoundError if missing

### `list_evidence(db, *, assessment_practice_id, assessment_id, review_status) -> (list, int)`
- Filter by assessment_practice_id, or by assessment_id (join through AssessmentPractice), or review_status
- Return (items, total)

### `delete_evidence(db, evidence_id) -> None`
- Only deletable when review_status is pending
- Remove file from disk, delete DB record

### `review_evidence(db, evidence_id, *, reviewer_id, review_status) -> Evidence`
- Set review_status, reviewer_id, reviewed_at
- Only allowed when current status is pending

## Tests (`tests/test_evidence_service.py`)
- Test each function with happy path and error cases
- Use in-memory approach (bytes content) for file operations
- Mock file system in tests via tmp_path fixture
