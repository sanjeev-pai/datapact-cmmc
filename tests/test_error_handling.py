"""Tests for global error handling — exception handlers and error response format."""

from sqlalchemy.orm import Session

from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


def _create_user(db: Session, role_names: list[str] | None = None) -> User:
    user = User(
        username="errtest",
        email="errtest@test.local",
        password_hash=hash_password("testpass123!"),
    )
    db.add(user)
    db.flush()
    for rname in (role_names or ["compliance_officer"]):
        role = db.query(Role).filter(Role.name == rname).first()
        if role is None:
            role = Role(name=rname)
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    return user


def _auth_header(user: User) -> dict:
    token = create_access_token(user.id, [r.name for r in user.roles])
    return {"Authorization": f"Bearer {token}"}


class TestValidationErrorHandler:
    """Test that validation errors return consistent JSON format."""

    def test_validation_error_returns_422_with_auth(self, client, db):
        user = _create_user(db)
        headers = _auth_header(user)
        # POST to assessments with empty body triggers validation
        response = client.post("/api/assessments", json={}, headers=headers)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "errors" in data

    def test_validation_error_on_login(self, client):
        # Missing required fields on unauthenticated endpoint
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_validation_error_on_register(self, client):
        # Partial body — missing required fields
        response = client.post("/api/auth/register", json={"username": "x"})
        assert response.status_code == 422
        data = response.json()
        assert data["error_code"] == "VALIDATION_ERROR"
        assert len(data["errors"]) > 0


class TestNotFoundErrorHandler:
    """Test that NotFoundError returns proper 404."""

    def test_unknown_assessment_returns_404(self, client, db):
        user = _create_user(db)
        headers = _auth_header(user)
        response = client.get("/api/assessments/nonexistent", headers=headers)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestHealthEndpoint:
    """Verify health still works with exception handlers in place."""

    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
