"""Pydantic schemas for CMMC reference data API."""

from pydantic import BaseModel


class DomainResponse(BaseModel):
    id: str
    domain_id: str
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class LevelResponse(BaseModel):
    id: str
    level: int
    name: str
    assessment_type: str
    description: str | None = None

    model_config = {"from_attributes": True}


class PracticeResponse(BaseModel):
    id: str
    practice_id: str
    domain_ref: str
    level: int
    title: str
    description: str | None = None
    assessment_objectives: list | None = None
    evidence_requirements: list | None = None
    nist_refs: list | None = None

    model_config = {"from_attributes": True}


class PracticeListResponse(BaseModel):
    id: str
    practice_id: str
    domain_ref: str
    level: int
    title: str

    model_config = {"from_attributes": True}
