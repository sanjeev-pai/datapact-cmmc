"""Tests for FastAPI auth dependencies."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cmmc.dependencies.auth import get_current_user, require_role, PermissionChecker
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_role(db: Session, name: str) -> Role:
    role = Role(name=name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def _create_user(
    db: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    role_names: list[str] | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
        is_active=is_active,
    )
    db.add(user)
    db.flush()

    for rname in (role_names or []):
        role = db.query(Role).filter(Role.name == rname).first()
        if role is None:
            role = _create_role(db, rname)
        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.add(user_role)

    db.commit()
    db.refresh(user)
    return user


def _make_token(user: User, roles: list[str] | None = None) -> str:
    role_names = roles if roles is not None else [r.name for r in user.roles]
    return create_access_token(user.id, role_names)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_app(db):
    """Minimal FastAPI app wired with auth dependencies for testing."""
    from cmmc.database import get_db

    test_app = FastAPI()

    def _override_db():
        try:
            yield db
        finally:
            pass

    test_app.dependency_overrides[get_db] = _override_db

    @test_app.get("/me")
    def me(user: User = Depends(get_current_user)):
        return {"id": user.id, "username": user.username}

    @test_app.get("/admin-only")
    def admin_only(user: User = Depends(require_role("system_admin", "org_admin"))):
        return {"id": user.id, "username": user.username}

    @test_app.get("/officer-only")
    def officer_only(user: User = Depends(require_role("compliance_officer"))):
        return {"id": user.id, "username": user.username}

    @test_app.get("/checked")
    def checked(
        user: User = Depends(
            PermissionChecker(roles=["system_admin", "org_admin"])
        ),
    ):
        return {"id": user.id, "username": user.username}

    return TestClient(test_app)


# ---------------------------------------------------------------------------
# get_current_user tests
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def test_valid_token_returns_user(self, db, auth_app):
        user = _create_user(db, role_names=["viewer"])
        token = _make_token(user)
        resp = auth_app.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == user.id
        assert resp.json()["username"] == "testuser"

    def test_missing_header_returns_401(self, auth_app):
        resp = auth_app.get("/me")
        assert resp.status_code == 401

    def test_empty_bearer_returns_401(self, auth_app):
        resp = auth_app.get("/me", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401

    def test_malformed_header_returns_401(self, auth_app):
        resp = auth_app.get("/me", headers={"Authorization": "Token abc"})
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, auth_app):
        resp = auth_app.get("/me", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    def test_nonexistent_user_returns_401(self, db, auth_app):
        token = create_access_token("nonexistent_id", ["viewer"])
        resp = auth_app.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self, db, auth_app):
        user = _create_user(db, role_names=["viewer"], is_active=False)
        token = _make_token(user)
        resp = auth_app.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_refresh_token_rejected(self, db, auth_app):
        from cmmc.services.auth_service import create_refresh_token
        user = _create_user(db, role_names=["viewer"])
        token = create_refresh_token(user.id)
        resp = auth_app.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# require_role tests
# ---------------------------------------------------------------------------

class TestRequireRole:
    def test_user_with_required_role_passes(self, db, auth_app):
        user = _create_user(db, role_names=["system_admin"])
        token = _make_token(user)
        resp = auth_app.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_user_with_any_matching_role_passes(self, db, auth_app):
        user = _create_user(db, role_names=["org_admin"])
        token = _make_token(user)
        resp = auth_app.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_user_without_required_role_returns_403(self, db, auth_app):
        user = _create_user(db, role_names=["viewer"])
        token = _make_token(user)
        resp = auth_app.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_no_auth_returns_401(self, auth_app):
        resp = auth_app.get("/admin-only")
        assert resp.status_code == 401

    def test_single_role_check(self, db, auth_app):
        user = _create_user(db, role_names=["compliance_officer"])
        token = _make_token(user)
        resp = auth_app.get("/officer-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_single_role_check_wrong_role(self, db, auth_app):
        user = _create_user(db, role_names=["viewer"])
        token = _make_token(user)
        resp = auth_app.get("/officer-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PermissionChecker tests
# ---------------------------------------------------------------------------

class TestPermissionChecker:
    def test_matching_role_passes(self, db, auth_app):
        user = _create_user(db, role_names=["system_admin"])
        token = _make_token(user)
        resp = auth_app.get("/checked", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_wrong_role_returns_403(self, db, auth_app):
        user = _create_user(db, role_names=["viewer"])
        token = _make_token(user)
        resp = auth_app.get("/checked", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_no_auth_returns_401(self, auth_app):
        resp = auth_app.get("/checked")
        assert resp.status_code == 401
