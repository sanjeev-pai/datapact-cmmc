"""POA&M (Plan of Action and Milestones) models."""

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class POAM(BaseModel):
    """A Plan of Action and Milestones for an organization."""

    __tablename__ = "poams"

    org_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("organizations.id"), nullable=False
    )
    assessment_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("assessments.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )

    organization: Mapped["Organization"] = relationship()  # noqa: F821
    assessment: Mapped["Assessment"] = relationship()  # noqa: F821
    items: Mapped[list["POAMItem"]] = relationship(back_populates="poam")


class POAMItem(BaseModel):
    """Individual item within a POA&M plan."""

    __tablename__ = "poam_items"

    poam_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("poams.id"), nullable=False
    )
    finding_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("findings.id"), nullable=True
    )
    practice_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    milestone: Mapped[str | None] = mapped_column(String(256), nullable=True)
    scheduled_completion: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_completion: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="open", nullable=False
    )
    resources_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_accepted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    poam: Mapped["POAM"] = relationship(back_populates="items")
    finding: Mapped["Finding"] = relationship()  # noqa: F821
