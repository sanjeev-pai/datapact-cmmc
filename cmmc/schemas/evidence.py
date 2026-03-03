"""Pydantic schemas for evidence API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReviewStatus = Literal["pending", "accepted", "rejected"]
ReviewAction = Literal["accepted", "rejected"]


class EvidenceCreate(BaseModel):
    assessment_practice_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    file_name: str | None = None
    file_size: int | None = Field(None, gt=0)
    mime_type: str | None = None


class EvidenceUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None


class EvidenceReview(BaseModel):
    review_status: ReviewAction


class EvidenceResponse(BaseModel):
    id: str
    assessment_practice_id: str
    title: str
    description: str | None = None
    file_path: str | None = None
    file_url: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    review_status: str
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    items: list[EvidenceResponse]
    total: int
