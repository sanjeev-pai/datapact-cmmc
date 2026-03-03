"""Tests for cmmc.services.auth_service."""

import time

import jwt
import pytest

from cmmc import config
from cmmc.errors import UnauthorizedError
from cmmc.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ── hash_password ────────────────────────────────────────────────────────────


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        hashed = hash_password("secret123")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts

    def test_empty_password_raises(self):
        with pytest.raises(ValueError):
            hash_password("")


# ── verify_password ──────────────────────────────────────────────────────────


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_returns_false(self):
        hashed = hash_password("notempty")
        assert verify_password("", hashed) is False


# ── create_access_token ──────────────────────────────────────────────────────


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token("user-1", ["admin"])
        assert isinstance(token, str)

    def test_payload_fields(self):
        token = create_access_token("user-1", ["admin", "viewer"])
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        assert payload["sub"] == "user-1"
        assert payload["roles"] == ["admin", "viewer"]
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token("user-1", ["admin"], expires_minutes=1)
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        # exp should be ~60 seconds from now, not the default
        remaining = payload["exp"] - time.time()
        assert remaining <= 60
        assert remaining > 0

    def test_empty_roles_allowed(self):
        token = create_access_token("user-1", [])
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        assert payload["roles"] == []


# ── create_refresh_token ─────────────────────────────────────────────────────


class TestCreateRefreshToken:
    def test_returns_string(self):
        token = create_refresh_token("user-1")
        assert isinstance(token, str)

    def test_payload_fields(self):
        token = create_refresh_token("user-1")
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "roles" not in payload

    def test_custom_expiry(self):
        token = create_refresh_token("user-1", expires_days=1)
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        remaining = payload["exp"] - time.time()
        # Should be roughly 1 day, not 7
        assert remaining <= 86400
        assert remaining > 86000


# ── decode_token ─────────────────────────────────────────────────────────────


class TestDecodeToken:
    def test_valid_access_token(self):
        token = create_access_token("user-1", ["admin"])
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"
        assert payload["roles"] == ["admin"]

    def test_valid_refresh_token(self):
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_expired_token_raises(self):
        token = create_access_token("user-1", ["admin"], expires_minutes=-1)
        with pytest.raises(UnauthorizedError):
            decode_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(UnauthorizedError):
            decode_token("not-a-jwt")

    def test_tampered_token_raises(self):
        token = create_access_token("user-1", ["admin"])
        tampered = token[:-4] + "XXXX"
        with pytest.raises(UnauthorizedError):
            decode_token(tampered)

    def test_empty_token_raises(self):
        with pytest.raises(UnauthorizedError):
            decode_token("")

    def test_wrong_secret_raises(self):
        payload = {"sub": "user-1", "type": "access", "roles": [], "exp": time.time() + 300}
        token = jwt.encode(payload, "wrong-secret", algorithm=config.JWT_ALGORITHM)
        with pytest.raises(UnauthorizedError):
            decode_token(token)

    def test_missing_sub_raises(self):
        payload = {"type": "access", "roles": [], "exp": time.time() + 300}
        token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
        with pytest.raises(UnauthorizedError):
            decode_token(token)

    def test_missing_type_raises(self):
        payload = {"sub": "user-1", "roles": [], "exp": time.time() + 300}
        token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
        with pytest.raises(UnauthorizedError):
            decode_token(token)
