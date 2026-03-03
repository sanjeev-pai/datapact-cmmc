"""Pydantic schemas for assessment API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AssessmentStatus = Literal["draft", "in_progress", "under_review", "completed"]
AssessmentType = Literal["self", "third_party", "government"]
PracticeStatus = Literal[
    "not_evaluated", "met", "not_met", "partially_met", "not_applicable"
]


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------


class AssessmentCreate(BaseModel):
    org_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=256)
    target_level: int = Field(..., ge=1, le=3)
    assessment_type: AssessmentType
    lead_assessor_id: str | None = None


class AssessmentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256)
    target_level: int | None = Field(None, ge=1, le=3)
    assessment_type: AssessmentType | None = None
    status: AssessmentStatus | None = None
    lead_assessor_id: str | None = None


class AssessmentResponse(BaseModel):
    id: str
    org_id: str
    title: str
    target_level: int
    assessment_type: str
    status: str
    lead_assessor_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    overall_score: float | None = None
    sprs_score: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssessmentListResponse(BaseModel):
    items: list[AssessmentResponse]
    total: int


# ---------------------------------------------------------------------------
# AssessmentPractice
# ---------------------------------------------------------------------------


class AssessmentPracticeUpdate(BaseModel):
    status: PracticeStatus | None = None
    score: float | None = Field(None, ge=0.0, le=1.0)
    assessor_notes: str | None = None


class AssessmentPracticeResponse(BaseModel):
    id: str
    assessment_id: str
    practice_id: str
    status: str
    score: float | None = None
    assessor_notes: str | None = None
    datapact_sync_status: str | None = None
    datapact_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
