"""User, Role, and UserRole models."""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cmmc.models.base import BaseModel


class Role(BaseModel):
    """Application role (compliance_officer, assessor, etc.)."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles", back_populates="roles"
    )


class User(BaseModel):
    """Application user."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    org_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("organizations.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="users")  # noqa: F821
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", back_populates="users"
    )


class UserRole(BaseModel):
    """Junction table for user-role many-to-many."""

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("roles.id"), nullable=False
    )
