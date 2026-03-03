"""Pydantic schemas for organization API."""

from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    cage_code: str | None = Field(None, max_length=8)
    duns_number: str | None = Field(None, max_length=16)
    target_level: int | None = Field(None, ge=1, le=3)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    cage_code: str | None = None
    duns_number: str | None = None
    target_level: int | None = Field(None, ge=1, le=3)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    cage_code: str | None = None
    duns_number: str | None = None
    target_level: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
