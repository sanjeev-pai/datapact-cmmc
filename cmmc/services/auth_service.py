"""Authentication service — password hashing and JWT token management."""

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from cmmc import config
from cmmc.errors import UnauthorizedError

logger = logging.getLogger(__name__)


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Raises ValueError if password is empty.
    """
    if not plain_password:
        raise ValueError("Password must not be empty")
    hashed = bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt())
    return hashed.decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Returns False for empty passwords rather than raising.
    """
    if not plain_password:
        return False
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def create_access_token(
    user_id: str,
    roles: list[str],
    expires_minutes: int | None = None,
) -> str:
    """Create a JWT access token with user_id, roles, and expiry."""
    expires = expires_minutes if expires_minutes is not None else config.JWT_EXPIRY_MINUTES
    payload = {
        "sub": user_id,
        "roles": roles,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    expires_days: int | None = None,
) -> str:
    """Create a JWT refresh token with user_id and expiry (no roles)."""
    expires = expires_days if expires_days is not None else config.JWT_REFRESH_EXPIRY_DAYS
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=expires),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Returns the payload dict on success.
    Raises UnauthorizedError on expiry, tampering, or missing required fields.
    """
    if not token:
        raise UnauthorizedError("Token is required")
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token")

    if "sub" not in payload:
        raise UnauthorizedError("Token missing subject")
    if "type" not in payload:
        raise UnauthorizedError("Token missing type")

    return payload
