"""Pydantic schemas for user admin API."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserAdminUpdate(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=128)
    email: EmailStr | None = None
    is_active: bool | None = None
    org_id: str | None = None
    roles: list[str] | None = None


class UserAdminResponse(BaseModel):
    id: str
    username: str
    email: str
    org_id: str | None = None
    is_active: bool
    roles: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserAdminResponse":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            org_id=user.org_id,
            is_active=user.is_active,
            roles=[r.name for r in user.roles],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
