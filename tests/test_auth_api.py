"""Tests for auth API endpoints."""

import pytest
from sqlalchemy.orm import Session

from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_viewer_role(db: Session) -> Role:
    """Ensure the 'viewer' role exists (default role on register)."""
    role = db.query(Role).filter(Role.name == "viewer").first()
    if role:
        return role
    role = Role(name="viewer")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def _create_user(
    db: Session,
    username: str = "existing",
    email: str = "existing@example.com",
    password: str = "password123",
    is_active: bool = True,
    role_names: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_active=is_active,
    )
    db.add(user)
    db.flush()

    for rname in (role_names or ["viewer"]):
        role = db.query(Role).filter(Role.name == rname).first()
        if role is None:
            role = Role(name=rname)
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))

    db.commit()
    db.refresh(user)
    return user


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_success(self, client, db):
        _seed_viewer_role(db)
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "strongpass1",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "viewer" in data["roles"]
        assert "id" in data

    def test_register_duplicate_username(self, client, db):
        _seed_viewer_role(db)
        _create_user(db, username="taken", email="a@example.com")
        resp = client.post("/api/auth/register", json={
            "username": "taken",
            "email": "b@example.com",
            "password": "strongpass1",
        })
        assert resp.status_code == 409

    def test_register_duplicate_email(self, client, db):
        _seed_viewer_role(db)
        _create_user(db, username="user1", email="taken@example.com")
        resp = client.post("/api/auth/register", json={
            "username": "user2",
            "email": "taken@example.com",
            "password": "strongpass1",
        })
        assert resp.status_code == 409

    def test_register_short_password(self, client, db):
        _seed_viewer_role(db)
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "short",
        })
        assert resp.status_code == 422

    def test_register_short_username(self, client, db):
        resp = client.post("/api/auth/register", json={
            "username": "ab",
            "email": "new@example.com",
            "password": "strongpass1",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client, db):
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "not-an-email",
            "password": "strongpass1",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success(self, client, db):
        _create_user(db, username="loginuser", email="login@example.com", password="mypassword1")
        resp = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "mypassword1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, db):
        _create_user(db, username="loginuser", email="login@example.com", password="correctpass")
        resp = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        resp = client.post("/api/auth/login", json={
            "username": "ghost",
            "password": "whatever1",
        })
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db):
        _create_user(db, username="inactive", email="inactive@example.com", password="mypassword1", is_active=False)
        resp = client.post("/api/auth/login", json={
            "username": "inactive",
            "password": "mypassword1",
        })
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    def test_refresh_success(self, client, db):
        user = _create_user(db)
        refresh = create_refresh_token(user.id)
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_rejected(self, client, db):
        user = _create_user(db)
        access = create_access_token(user.id, ["viewer"])
        resp = client.post("/api/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401

    def test_refresh_invalid_token(self, client, db):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "bad.token.here"})
        assert resp.status_code == 401

    def test_refresh_nonexistent_user(self, client, db):
        refresh = create_refresh_token("nonexistent_id")
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    def test_me_authenticated(self, client, db):
        user = _create_user(db, username="meuser", email="me@example.com")
        token = create_access_token(user.id, [r.name for r in user.roles])
        resp = client.get("/api/auth/me", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "meuser"
        assert data["email"] == "me@example.com"
        assert "viewer" in data["roles"]

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/auth/me
# ---------------------------------------------------------------------------

class TestPatchMe:
    def test_update_email(self, client, db):
        user = _create_user(db, username="patchuser", email="old@example.com")
        token = create_access_token(user.id, [r.name for r in user.roles])
        resp = client.patch(
            "/api/auth/me",
            json={"email": "new@example.com"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@example.com"

    def test_update_username(self, client, db):
        user = _create_user(db, username="oldname", email="patch@example.com")
        token = create_access_token(user.id, [r.name for r in user.roles])
        resp = client.patch(
            "/api/auth/me",
            json={"username": "newname"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "newname"

    def test_update_duplicate_username_returns_409(self, client, db):
        _create_user(db, username="taken", email="taken@example.com")
        user = _create_user(db, username="other", email="other@example.com")
        token = create_access_token(user.id, [r.name for r in user.roles])
        resp = client.patch(
            "/api/auth/me",
            json={"username": "taken"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 409

    def test_update_duplicate_email_returns_409(self, client, db):
        _create_user(db, username="taken2", email="taken2@example.com")
        user = _create_user(db, username="other2", email="other2@example.com")
        token = create_access_token(user.id, [r.name for r in user.roles])
        resp = client.patch(
            "/api/auth/me",
            json={"email": "taken2@example.com"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 409

    def test_update_unauthenticated(self, client):
        resp = client.patch("/api/auth/me", json={"username": "new"})
        assert resp.status_code == 401

    def test_empty_update(self, client, db):
        user = _create_user(db, username="emptyup", email="empty@example.com")
        token = create_access_token(user.id, [r.name for r in user.roles])
        resp = client.patch(
            "/api/auth/me",
            json={},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "emptyup"
