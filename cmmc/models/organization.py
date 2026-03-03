"""Organization model."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class Organization(BaseModel):
    """Organization pursuing CMMC certification."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    cage_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    duns_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    datapact_api_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    datapact_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")  # noqa: F821
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="organization")  # noqa: F821
