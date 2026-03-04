"""Tests for audit logging middleware and API endpoint."""

from sqlalchemy.orm import Session

from cmmc.models.audit import AuditLog
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(
    db: Session,
    username: str = "audituser",
    role_names: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
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


# ---------------------------------------------------------------------------
# Middleware unit tests
# ---------------------------------------------------------------------------

class TestAuditMiddlewareHelpers:
    """Test middleware utility functions directly."""

    def test_extract_resource_simple(self):
        from cmmc.middleware.audit import _extract_resource
        rt, rid = _extract_resource("/api/assessments")
        assert rt == "assessments"
        assert rid is None

    def test_extract_resource_with_id(self):
        from cmmc.middleware.audit import _extract_resource
        rt, rid = _extract_resource("/api/assessments/abc123")
        assert rt == "assessments"
        assert rid == "abc123"

    def test_extract_resource_nested(self):
        from cmmc.middleware.audit import _extract_resource
        rt, rid = _extract_resource("/api/poams/x/items/y")
        assert rt == "poams"
        assert rid == "x"

    def test_action_from_method(self):
        from cmmc.middleware.audit import _action_from_method
        assert _action_from_method("POST") == "create"
        assert _action_from_method("PATCH") == "update"
        assert _action_from_method("PUT") == "update"
        assert _action_from_method("DELETE") == "delete"


class TestAuditMiddlewareIntegration:
    """Test middleware via HTTP client — verifies audit logs are written."""

    def test_successful_post_creates_audit_log(self, client, db):
        """Register a user (unauthenticated POST) and verify audit log."""
        # Seed the viewer role needed by register endpoint
        if not db.query(Role).filter(Role.name == "viewer").first():
            db.add(Role(name="viewer"))
            db.commit()

        resp = client.post("/api/auth/register", json={
            "username": "auditee",
            "email": "auditee@example.com",
            "password": "password123!",
        })
        assert resp.status_code == 201

        # Middleware writes via its own session; expire to see the writes
        db.expire_all()
        logs = db.query(AuditLog).all()
        assert len(logs) >= 1
        log = logs[0]
        assert log.action == "create"
        assert log.resource_type == "auth"
        assert log.details["method"] == "POST"

    def test_get_does_not_create_audit_log(self, client, db):
        client.get("/api/health")
        db.expire_all()
        assert db.query(AuditLog).count() == 0

    def test_failed_post_not_logged(self, client, db):
        """4xx should not be audited."""
        # Missing fields → 422
        client.post("/api/auth/login", json={})
        db.expire_all()
        assert db.query(AuditLog).count() == 0

    def test_audit_captures_user_id_from_jwt(self, client, db):
        """Authenticated write should capture user_id."""
        # Seed roles
        for rname in ["viewer", "system_admin"]:
            if not db.query(Role).filter(Role.name == rname).first():
                db.add(Role(name=rname))
        db.commit()

        admin = _create_user(db, username="admin_audit", role_names=["system_admin"])
        headers = _auth_header(admin)

        # Use auth/register endpoint authenticated (token is optional but present)
        client.post("/api/auth/register", json={
            "username": "u99",
            "email": "u99@example.com",
            "password": "password123!",
        }, headers=headers)

        db.expire_all()
        log = db.query(AuditLog).first()
        assert log is not None
        assert log.user_id == admin.id


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestAuditLogRouter:
    """Test GET /api/audit-log endpoint."""

    def _seed_audit_log(self, db, user_id: str = "u1") -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action="create",
            resource_type="assessments",
            resource_id="a1",
            details={"method": "POST", "path": "/api/assessments", "status_code": 201},
            ip_address="127.0.0.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def test_admin_can_list_audit_logs(self, client, db):
        admin = _create_user(db, username="adm", role_names=["system_admin"])
        headers = _auth_header(admin)
        self._seed_audit_log(db, user_id=admin.id)

        response = client.get("/api/audit-log", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_non_admin_cannot_list_audit_logs(self, client, db):
        viewer = _create_user(db, username="viewer", role_names=["viewer"])
        headers = _auth_header(viewer)

        response = client.get("/api/audit-log", headers=headers)
        assert response.status_code == 403

    def test_filter_by_action(self, client, db):
        admin = _create_user(db, username="adm2", role_names=["system_admin"])
        headers = _auth_header(admin)
        self._seed_audit_log(db, user_id=admin.id)

        response = client.get("/api/audit-log?action=create", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

        response = client.get("/api/audit-log?action=delete", headers=headers)
        assert response.json()["total"] == 0

    def test_filter_by_resource_type(self, client, db):
        admin = _create_user(db, username="adm3", role_names=["system_admin"])
        headers = _auth_header(admin)
        self._seed_audit_log(db, user_id=admin.id)

        response = client.get("/api/audit-log?resource_type=assessments", headers=headers)
        assert response.json()["total"] >= 1

    def test_get_single_audit_log(self, client, db):
        admin = _create_user(db, username="adm4", role_names=["system_admin"])
        headers = _auth_header(admin)
        log = self._seed_audit_log(db, user_id=admin.id)

        response = client.get(f"/api/audit-log/{log.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == log.id
        assert data["action"] == "create"

    def test_get_nonexistent_audit_log(self, client, db):
        admin = _create_user(db, username="adm5", role_names=["system_admin"])
        headers = _auth_header(admin)

        response = client.get("/api/audit-log/nonexistent", headers=headers)
        assert response.status_code == 404

    def test_pagination(self, client, db):
        admin = _create_user(db, username="adm6", role_names=["system_admin"])
        headers = _auth_header(admin)
        for _ in range(3):
            self._seed_audit_log(db, user_id=admin.id)

        response = client.get("/api/audit-log?limit=2&offset=0", headers=headers)
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) == 2
