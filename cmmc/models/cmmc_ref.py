"""CMMC reference data models — domains, levels, practices."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class CMMCDomain(BaseModel):
    """One of 14 CMMC security domains (AC, AT, AU, …)."""

    __tablename__ = "cmmc_domains"

    domain_id: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    practices: Mapped[list["CMMCPractice"]] = relationship(
        back_populates="domain", foreign_keys="CMMCPractice.domain_ref"
    )


class CMMCLevel(BaseModel):
    """CMMC maturity level (1, 2, or 3)."""

    __tablename__ = "cmmc_levels"

    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CMMCPractice(BaseModel):
    """Individual CMMC practice (e.g. AC.L1-3.1.1)."""

    __tablename__ = "cmmc_practices"

    practice_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    domain_ref: Mapped[str] = mapped_column(
        String(4), ForeignKey("cmmc_domains.domain_id"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_objectives: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    nist_refs: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    domain: Mapped["CMMCDomain"] = relationship(
        back_populates="practices", foreign_keys=[domain_ref]
    )
