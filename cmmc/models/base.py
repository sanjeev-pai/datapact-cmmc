"""Base model with id, timestamps, creator, and row versioning."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all CMMC models."""

    pass


class TimestampMixin:
    """created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class CreatorMixin:
    """Tracks who created the row."""

    creator_id: Mapped[str] = mapped_column(
        String(128), default="system", server_default="system", nullable=False
    )


class VersionMixin:
    """Row-level version counter for optimistic locking."""

    row_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )


class BaseModel(Base, TimestampMixin, CreatorMixin, VersionMixin):
    """Abstract base — id (16-char hex UUID) + timestamps + creator + version."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: uuid.uuid4().hex[:16]
    )


# Auto-increment row_version on modifications
@event.listens_for(Session, "before_flush")
def _auto_increment_row_version(session, flush_context, instances):
    for obj in session.dirty:
        if isinstance(obj, BaseModel) and session.is_modified(
            obj, include_collections=False
        ):
            obj.row_version = (obj.row_version or 1) + 1
