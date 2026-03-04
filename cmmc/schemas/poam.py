"""Pydantic schemas for POA&M (Plan of Action and Milestones) API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

POAMStatus = Literal["draft", "active", "completed"]
POAMItemStatus = Literal["open", "in_progress", "completed"]

# ---------------------------------------------------------------------------
# POA&M
# ---------------------------------------------------------------------------


class POAMCreate(BaseModel):
    org_id: str = Field(..., min_length=1)
    assessment_id: str | None = None
    title: str = Field(..., min_length=1, max_length=256)


class POAMUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256)
    status: POAMStatus | None = None


class POAMResponse(BaseModel):
    id: str
    org_id: str
    assessment_id: str | None = None
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class POAMDetailResponse(POAMResponse):
    """POA&M with nested items."""

    items: list["POAMItemResponse"] = []


class POAMListResponse(BaseModel):
    items: list[POAMResponse]
    total: int


# ---------------------------------------------------------------------------
# POA&M Item
# ---------------------------------------------------------------------------


class POAMItemCreate(BaseModel):
    finding_id: str | None = None
    practice_id: str | None = Field(None, max_length=32)
    milestone: str | None = Field(None, max_length=256)
    scheduled_completion: date | None = None
    resources_required: str | None = None
    risk_accepted: bool = False


class POAMItemUpdate(BaseModel):
    milestone: str | None = Field(None, max_length=256)
    scheduled_completion: date | None = None
    actual_completion: date | None = None
    status: POAMItemStatus | None = None
    resources_required: str | None = None
    risk_accepted: bool | None = None


class POAMItemResponse(BaseModel):
    id: str
    poam_id: str
    finding_id: str | None = None
    practice_id: str | None = None
    milestone: str | None = None
    scheduled_completion: date | None = None
    actual_completion: date | None = None
    status: str
    resources_required: str | None = None
    risk_accepted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
