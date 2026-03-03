"""Finding model."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class Finding(BaseModel):
    """A finding from an assessment (deficiency, observation, etc.)."""

    __tablename__ = "findings"

    assessment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("assessments.id"), nullable=False
    )
    practice_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="open", nullable=False
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="findings")  # noqa: F821
