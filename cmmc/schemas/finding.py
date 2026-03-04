"""Pydantic schemas for Finding API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

FindingType = Literal["deficiency", "observation", "recommendation"]
FindingSeverity = Literal["high", "medium", "low"]
FindingStatus = Literal["open", "resolved", "accepted_risk"]

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class FindingCreate(BaseModel):
    assessment_id: str = Field(..., min_length=1)
    practice_id: str | None = Field(None, max_length=32)
    finding_type: FindingType
    severity: FindingSeverity
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = None


class FindingUpdate(BaseModel):
    practice_id: str | None = Field(None, max_length=32)
    finding_type: FindingType | None = None
    severity: FindingSeverity | None = None
    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    status: FindingStatus | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class FindingResponse(BaseModel):
    id: str
    assessment_id: str
    practice_id: str | None = None
    finding_type: str
    severity: str
    title: str
    description: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FindingListResponse(BaseModel):
    items: list[FindingResponse]
    total: int
