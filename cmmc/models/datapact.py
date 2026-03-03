"""DataPact integration models."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from cmmc.models.base import BaseModel


class DataPactPracticeMapping(BaseModel):
    """Maps a CMMC practice to a DataPact contract."""

    __tablename__ = "datapact_practice_mappings"

    org_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("organizations.id"), nullable=False
    )
    practice_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("cmmc_practices.practice_id"), nullable=False
    )
    datapact_contract_id: Mapped[str] = mapped_column(String(128), nullable=False)
    datapact_contract_name: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )


class DataPactSyncLog(BaseModel):
    """Log entry for a DataPact sync operation."""

    __tablename__ = "datapact_sync_logs"

    org_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("organizations.id"), nullable=False
    )
    assessment_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("assessments.id"), nullable=True
    )
    practice_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
