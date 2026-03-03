"""Pydantic schemas for DataPact integration API."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Mapping schemas ──────────────────────────────────────────────────────────


class MappingCreate(BaseModel):
    practice_id: str = Field(..., min_length=1)
    datapact_contract_id: str = Field(..., min_length=1)
    datapact_contract_name: str | None = None


class MappingResponse(BaseModel):
    id: str
    org_id: str
    practice_id: str
    datapact_contract_id: str
    datapact_contract_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MappingListResponse(BaseModel):
    items: list[MappingResponse]
    total: int


# ── Sync schemas ─────────────────────────────────────────────────────────────


class SyncResultResponse(BaseModel):
    practice_id: str
    status: str
    message: str | None = None
    compliance: dict | None = None


class SyncResultsResponse(BaseModel):
    results: list[SyncResultResponse]


# ── Sync log schemas ─────────────────────────────────────────────────────────


class SyncLogResponse(BaseModel):
    id: str
    org_id: str
    assessment_id: str | None = None
    practice_id: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncLogListResponse(BaseModel):
    items: list[SyncLogResponse]
    total: int


# ── Suggest schemas ──────────────────────────────────────────────────────────


class SuggestionResponse(BaseModel):
    practice_id: str
    contract_id: str
    contract_name: str | None = None
    reason: str | None = None
