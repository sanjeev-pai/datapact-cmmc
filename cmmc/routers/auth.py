"""Auth API endpoints — register, login, refresh, profile."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user
from cmmc.errors import ConflictError, UnauthorizedError
from cmmc.models.user import Role, User, UserRole
from cmmc.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from cmmc.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user with the default 'viewer' role."""
    # Check uniqueness
    if db.query(User).filter(User.username == body.username).first():
        raise ConflictError("Username already taken")
    if db.query(User).filter(User.email == body.email).first():
        raise ConflictError("Email already registered")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()

    # Assign default viewer role
    viewer_role = db.query(Role).filter(Role.name == "viewer").first()
    if viewer_role:
        db.add(UserRole(user_id=user.id, role_id=viewer_role.id))

    db.commit()
    db.refresh(user)
    return UserResponse.from_user(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with username/password, receive access + refresh tokens."""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    role_names = [r.name for r in user.roles]
    return TokenResponse(
        access_token=create_access_token(user.id, role_names),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive")

    role_names = [r.name for r in user.roles]
    return TokenResponse(
        access_token=create_access_token(user.id, role_names),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return UserResponse.from_user(user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    body: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile fields."""
    if body.username is not None and body.username != user.username:
        if db.query(User).filter(User.username == body.username, User.id != user.id).first():
            raise ConflictError("Username already taken")
        user.username = body.username

    if body.email is not None and body.email != user.email:
        if db.query(User).filter(User.email == body.email, User.id != user.id).first():
            raise ConflictError("Email already registered")
        user.email = body.email

    db.commit()
    db.refresh(user)
    return UserResponse.from_user(user)
