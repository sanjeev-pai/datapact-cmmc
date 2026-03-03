"""Tests for user admin API endpoints."""

from sqlalchemy.orm import Session

from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.flush()
    return role


def _create_user(
    db: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "password123",
    org_id: str | None = None,
    role_names: list[str] | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        org_id=org_id,
        is_active=is_active,
    )
    db.add(user)
    db.flush()

    for rname in (role_names or ["viewer"]):
        role = _create_role(db, rname)
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
# GET /api/users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_list_system_admin_sees_all(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        _create_user(db, username="u1", email="u1@e.com", org_id=org1.id, role_names=["viewer"])
        _create_user(db, username="u2", email="u2@e.com", org_id=org2.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.get("/api/users", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 200
        data = resp.json()
        usernames = {u["username"] for u in data}
        assert "u1" in usernames
        assert "u2" in usernames
        assert "admin" in usernames

    def test_list_org_admin_sees_own_org(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        _create_user(db, username="u1", email="u1@e.com", org_id=org1.id, role_names=["viewer"])
        _create_user(db, username="u2", email="u2@e.com", org_id=org2.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org1.id, role_names=["org_admin"])

        resp = client.get("/api/users", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 200
        data = resp.json()
        usernames = {u["username"] for u in data}
        assert "u1" in usernames
        assert "orgadmin" in usernames
        assert "u2" not in usernames

    def test_list_viewer_forbidden(self, client, db):
        org = _create_org(db, name="Org")
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.get("/api/users", headers=_auth_header(_token_for(user)))
        assert resp.status_code == 403

    def test_list_unauthenticated(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/users/{id}
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_get_system_admin_any_user(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.get(f"/api/users/{target.id}", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "target"
        assert data["email"] == "target@e.com"
        assert "viewer" in data["roles"]

    def test_get_org_admin_own_org_user(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org.id, role_names=["org_admin"])

        resp = client.get(f"/api/users/{target.id}", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 200
        assert resp.json()["username"] == "target"

    def test_get_org_admin_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        target = _create_user(db, username="target", email="target@e.com", org_id=org2.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org1.id, role_names=["org_admin"])

        resp = client.get(f"/api/users/{target.id}", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 403

    def test_get_not_found(self, client, db):
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])
        resp = client.get("/api/users/nonexistent", headers=_auth_header(_token_for(admin)))
        assert resp.status_code == 404

    def test_get_viewer_forbidden(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        viewer = _create_user(db, username="viewer", email="v@e.com", org_id=org.id, role_names=["viewer"])
        resp = client.get(f"/api/users/{target.id}", headers=_auth_header(_token_for(viewer)))
        assert resp.status_code == 403

    def test_get_unauthenticated(self, client):
        resp = client.get("/api/users/someid")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/users/{id}
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_update_username_system_admin(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="oldname", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"username": "newname"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "newname"

    def test_update_email(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="old@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"email": "new@e.com"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "new@e.com"

    def test_update_is_active(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"is_active": False},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_roles(self, client, db):
        org = _create_org(db, name="Org")
        _create_role(db, "assessor")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"roles": ["assessor", "viewer"]},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert set(resp.json()["roles"]) == {"assessor", "viewer"}

    def test_update_org_id_system_admin(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        target = _create_user(db, username="target", email="target@e.com", org_id=org1.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"org_id": org2.id},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["org_id"] == org2.id

    def test_update_org_admin_own_org_user(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org.id, role_names=["org_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"username": "updated"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "updated"

    def test_update_org_admin_cannot_assign_system_admin_role(self, client, db):
        org = _create_org(db, name="Org")
        _create_role(db, "system_admin")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org.id, role_names=["org_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"roles": ["system_admin"]},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 403

    def test_update_org_admin_cannot_change_org_id(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        target = _create_user(db, username="target", email="target@e.com", org_id=org1.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org1.id, role_names=["org_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"org_id": org2.id},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 403

    def test_update_org_admin_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        target = _create_user(db, username="target", email="target@e.com", org_id=org2.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org1.id, role_names=["org_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"username": "hacked"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 403

    def test_update_viewer_forbidden(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        viewer = _create_user(db, username="viewer", email="v@e.com", org_id=org.id, role_names=["viewer"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"username": "hacked"},
            headers=_auth_header(_token_for(viewer)),
        )
        assert resp.status_code == 403

    def test_update_duplicate_username(self, client, db):
        org = _create_org(db, name="Org")
        _create_user(db, username="existing", email="existing@e.com", org_id=org.id, role_names=["viewer"])
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"username": "existing"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 409

    def test_update_duplicate_email(self, client, db):
        org = _create_org(db, name="Org")
        _create_user(db, username="existing", email="taken@e.com", org_id=org.id, role_names=["viewer"])
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"email": "taken@e.com"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 409

    def test_update_not_found(self, client, db):
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])
        resp = client.patch(
            "/api/users/nonexistent",
            json={"username": "nope"},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 404

    def test_update_empty_body(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="unchanged", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "unchanged"

    def test_update_unauthenticated(self, client):
        resp = client.patch("/api/users/someid", json={"username": "nope"})
        assert resp.status_code == 401

    def test_update_invalid_role(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.patch(
            f"/api/users/{target.id}",
            json={"roles": ["nonexistent_role"]},
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/users/{id} (deactivate)
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_deactivate_system_admin(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.delete(
            f"/api/users/{target.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 204
        # Verify user still exists but is inactive
        db.refresh(target)
        assert target.is_active is False

    def test_deactivate_org_admin_own_org(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org.id, role_names=["org_admin"])

        resp = client.delete(
            f"/api/users/{target.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 204
        db.refresh(target)
        assert target.is_active is False

    def test_deactivate_self_forbidden(self, client, db):
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])
        resp = client.delete(
            f"/api/users/{admin.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 403

    def test_deactivate_org_admin_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        target = _create_user(db, username="target", email="target@e.com", org_id=org2.id, role_names=["viewer"])
        admin = _create_user(db, username="orgadmin", email="oa@e.com", org_id=org1.id, role_names=["org_admin"])

        resp = client.delete(
            f"/api/users/{target.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 403

    def test_deactivate_viewer_forbidden(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"])
        viewer = _create_user(db, username="viewer", email="v@e.com", org_id=org.id, role_names=["viewer"])

        resp = client.delete(
            f"/api/users/{target.id}",
            headers=_auth_header(_token_for(viewer)),
        )
        assert resp.status_code == 403

    def test_deactivate_not_found(self, client, db):
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])
        resp = client.delete(
            "/api/users/nonexistent",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 404

    def test_deactivate_already_inactive(self, client, db):
        org = _create_org(db, name="Org")
        target = _create_user(db, username="target", email="target@e.com", org_id=org.id, role_names=["viewer"], is_active=False)
        admin = _create_user(db, username="admin", email="admin@e.com", role_names=["system_admin"])

        resp = client.delete(
            f"/api/users/{target.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 204

    def test_deactivate_unauthenticated(self, client):
        resp = client.delete("/api/users/someid")
        assert resp.status_code == 401
