"""Evidence model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class Evidence(BaseModel):
    """Evidence artifact attached to a practice evaluation."""

    __tablename__ = "evidence"

    assessment_practice_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("assessment_practices.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )
    reviewer_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    assessment_practice: Mapped["AssessmentPractice"] = relationship(  # noqa: F821
        back_populates="evidence_items"
    )
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])  # noqa: F821
