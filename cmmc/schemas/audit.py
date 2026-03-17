"""Pydantic schemas for audit log endpoints."""

from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


class UnifiedAuditEntry(BaseModel):
    """A single entry in the unified audit log (CMMC or DataPact source)."""
    id: str
    source: str  # "cmmc" or "datapact"
    user_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnifiedAuditResponse(BaseModel):
    """Merged audit log from CMMC and DataPact sources."""
    items: list[UnifiedAuditEntry]
    total: int
    cmmc_total: int
    datapact_total: int
    datapact_available: bool
