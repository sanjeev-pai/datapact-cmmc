"""Pydantic schemas for auth API."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    org_id: str | None = None
    is_active: bool
    roles: list[str] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            org_id=user.org_id,
            is_active=user.is_active,
            roles=[r.name for r in user.roles],
        )


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=128)
    email: EmailStr | None = None
