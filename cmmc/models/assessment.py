"""Assessment and AssessmentPractice models."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class Assessment(BaseModel):
    """A CMMC assessment for an organization."""

    __tablename__ = "assessments"

    org_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )
    lead_assessor_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sprs_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="assessments")  # noqa: F821
    lead_assessor: Mapped["User"] = relationship(foreign_keys=[lead_assessor_id])  # noqa: F821
    practices: Mapped[list["AssessmentPractice"]] = relationship(
        back_populates="assessment"
    )
    findings: Mapped[list["Finding"]] = relationship(back_populates="assessment")  # noqa: F821


class AssessmentPractice(BaseModel):
    """Evaluation of a single practice within an assessment."""

    __tablename__ = "assessment_practices"

    assessment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("assessments.id"), nullable=False
    )
    practice_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("cmmc_practices.practice_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="not_evaluated", nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    datapact_sync_status: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    datapact_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="practices")
    practice: Mapped["CMMCPractice"] = relationship(foreign_keys=[practice_id])  # noqa: F821
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="assessment_practice")  # noqa: F821
