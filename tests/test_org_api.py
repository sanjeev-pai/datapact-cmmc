"""Tests for organization API endpoints."""

from sqlalchemy.orm import Session

from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(
    db: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "password123",
    org_id: str | None = None,
    role_names: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        org_id=org_id,
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


def _token_for(user: User) -> str:
    return create_access_token(user.id, [r.name for r in user.roles])


def _create_org(db: Session, name: str = "Acme Corp", **kwargs) -> Organization:
    org = Organization(name=name, **kwargs)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


# ---------------------------------------------------------------------------
# POST /api/organizations
# ---------------------------------------------------------------------------

class TestCreateOrganization:
    def test_create_success_system_admin(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "cage_code": "ABC12345", "target_level": 2},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme Corp"
        assert data["cage_code"] == "ABC12345"
        assert data["target_level"] == 2
        assert "id" in data
        assert "created_at" in data

    def test_create_forbidden_non_admin(self, client, db):
        user = _create_user(db, role_names=["viewer"])
        resp = client.post(
            "/api/organizations",
            json={"name": "Acme Corp"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_create_forbidden_org_admin(self, client, db):
        user = _create_user(db, role_names=["org_admin"])
        resp = client.post(
            "/api/organizations",
            json={"name": "Acme Corp"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_create_unauthenticated(self, client):
        resp = client.post("/api/organizations", json={"name": "Acme Corp"})
        assert resp.status_code == 401

    def test_create_duplicate_name(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        _create_org(db, name="Existing Org")
        resp = client.post(
            "/api/organizations",
            json={"name": "Existing Org"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 409

    def test_create_missing_name(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.post(
            "/api/organizations",
            json={},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 422

    def test_create_invalid_target_level(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.post(
            "/api/organizations",
            json={"name": "Acme", "target_level": 5},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 422

    def test_create_minimal(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.post(
            "/api/organizations",
            json={"name": "Minimal Org"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["cage_code"] is None
        assert data["duns_number"] is None
        assert data["target_level"] is None


# ---------------------------------------------------------------------------
# GET /api/organizations
# ---------------------------------------------------------------------------

class TestListOrganizations:
    def test_list_system_admin_sees_all(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.get("/api/organizations", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 200
        data = resp.json()
        names = {o["name"] for o in data}
        assert "Org A" in names
        assert "Org B" in names

    def test_list_regular_user_sees_own_org(self, client, db):
        org1 = _create_org(db, name="My Org")
        _create_org(db, name="Other Org")
        user = _create_user(db, org_id=org1.id, role_names=["viewer"])
        resp = client.get("/api/organizations", headers=_auth_header(_token_for(user)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "My Org"

    def test_list_user_without_org_sees_empty(self, client, db):
        _create_org(db, name="Some Org")
        user = _create_user(db, role_names=["viewer"])
        resp = client.get("/api/organizations", headers=_auth_header(_token_for(user)))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_unauthenticated(self, client):
        resp = client.get("/api/organizations")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/organizations/{id}
# ---------------------------------------------------------------------------

class TestGetOrganization:
    def test_get_system_admin_any_org(self, client, db):
        org = _create_org(db, name="Target Org", cage_code="XYZ")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.get(f"/api/organizations/{org.id}", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Target Org"
        assert resp.json()["cage_code"] == "XYZ"

    def test_get_user_own_org(self, client, db):
        org = _create_org(db, name="My Org")
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.get(f"/api/organizations/{org.id}", headers=_auth_header(_token_for(user)))
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Org"

    def test_get_user_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        user = _create_user(db, org_id=org1.id, role_names=["viewer"])
        resp = client.get(f"/api/organizations/{org2.id}", headers=_auth_header(_token_for(user)))
        assert resp.status_code == 403

    def test_get_not_found(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.get("/api/organizations/nonexistent", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 404

    def test_get_unauthenticated(self, client):
        resp = client.get("/api/organizations/someid")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/organizations/{id}
# ---------------------------------------------------------------------------

class TestUpdateOrganization:
    def test_update_system_admin(self, client, db):
        org = _create_org(db, name="Old Name")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.patch(
            f"/api/organizations/{org.id}",
            json={"name": "New Name", "target_level": 3},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["target_level"] == 3

    def test_update_org_admin_own_org(self, client, db):
        org = _create_org(db, name="My Org")
        user = _create_user(db, org_id=org.id, role_names=["org_admin"])
        resp = client.patch(
            f"/api/organizations/{org.id}",
            json={"cage_code": "NEWCODE"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["cage_code"] == "NEWCODE"

    def test_update_org_admin_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        user = _create_user(db, org_id=org1.id, role_names=["org_admin"])
        resp = client.patch(
            f"/api/organizations/{org2.id}",
            json={"name": "Hacked"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_update_viewer_forbidden(self, client, db):
        org = _create_org(db, name="My Org")
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.patch(
            f"/api/organizations/{org.id}",
            json={"name": "Hacked"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_update_not_found(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.patch(
            "/api/organizations/nonexistent",
            json={"name": "Nope"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 404

    def test_update_duplicate_name(self, client, db):
        _create_org(db, name="Existing")
        org = _create_org(db, name="Target")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.patch(
            f"/api/organizations/{org.id}",
            json={"name": "Existing"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 409

    def test_update_empty_body(self, client, db):
        org = _create_org(db, name="Unchanged")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.patch(
            f"/api/organizations/{org.id}",
            json={},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Unchanged"

    def test_update_unauthenticated(self, client):
        resp = client.patch("/api/organizations/someid", json={"name": "Nope"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/organizations/{id}
# ---------------------------------------------------------------------------

class TestDeleteOrganization:
    def test_delete_system_admin(self, client, db):
        org = _create_org(db, name="To Delete")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.delete(
            f"/api/organizations/{org.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 204
        # Verify deleted
        assert db.query(Organization).filter(Organization.id == org.id).first() is None

    def test_delete_forbidden_org_admin(self, client, db):
        org = _create_org(db, name="My Org")
        user = _create_user(db, org_id=org.id, role_names=["org_admin"])
        resp = client.delete(
            f"/api/organizations/{org.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_delete_forbidden_viewer(self, client, db):
        org = _create_org(db, name="My Org")
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.delete(
            f"/api/organizations/{org.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_delete_not_found(self, client, db):
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.delete(
            "/api/organizations/nonexistent",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 404

    def test_delete_unauthenticated(self, client):
        resp = client.delete("/api/organizations/someid")
        assert resp.status_code == 401
