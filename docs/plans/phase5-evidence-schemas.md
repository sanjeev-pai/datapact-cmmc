# Plan: phase5/evidence-schemas

## Objective
Create Pydantic schemas for the evidence API: create, update, response, and list response.

## Schemas

### `EvidenceCreate`
- assessment_practice_id: str (required)
- title: str (required, 1-256 chars)
- description: str | None (optional)
- file_name: str | None (optional, for metadata)
- file_size: int | None (optional, bytes)
- mime_type: str | None (optional)

### `EvidenceUpdate`
- title: str | None
- description: str | None
- file_name: str | None
- file_size: int | None
- mime_type: str | None

### `EvidenceReview`
- review_status: Literal["accepted", "rejected"]

### `EvidenceResponse`
- All model fields + created_at/updated_at
- from_attributes = True

### `EvidenceListResponse`
- items: list[EvidenceResponse]
- total: int

### ReviewStatus type
- Literal["pending", "accepted", "rejected"]

## Files
- NEW: `cmmc/schemas/evidence.py`
- NEW: `tests/test_evidence_schemas.py`

## Pattern
Follow existing schema conventions from `cmmc/schemas/assessment.py`:
- Field() with validation constraints
- model_config = {"from_attributes": True} on response models
- Separate Create/Update/Response classes
