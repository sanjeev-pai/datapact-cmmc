"""Tests for POA&M API endpoints."""

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment
from cmmc.models.finding import Finding
from cmmc.models.organization import Organization
from cmmc.models.poam import POAM, POAMItem
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(
    db: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    org_id: str | None = None,
    role_names: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
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


def _auth_header(user: User) -> dict:
    token = create_access_token(user.id, [r.name for r in user.roles])
    return {"Authorization": f"Bearer {token}"}


def _create_org(db: Session, name: str = "Acme Corp") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _create_poam(
    db: Session, org_id: str, title: str = "Test POA&M", status: str = "draft",
    assessment_id: str | None = None,
) -> POAM:
    poam = POAM(org_id=org_id, title=title, status=status, assessment_id=assessment_id)
    db.add(poam)
    db.commit()
    db.refresh(poam)
    return poam


def _create_item(
    db: Session, poam_id: str, milestone: str = "Test Item", status: str = "open",
) -> POAMItem:
    item = POAMItem(poam_id=poam_id, milestone=milestone, status=status, risk_accepted=False)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _create_assessment(db: Session, org_id: str) -> Assessment:
    a = Assessment(
        org_id=org_id, title="L2 Assessment", target_level=2,
        assessment_type="self", status="completed",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _create_finding(db: Session, assessment_id: str, title: str = "Finding 1") -> Finding:
    f = Finding(
        assessment_id=assessment_id, practice_id="AC.L2-3.1.1",
        finding_type="deficiency", severity="high", title=title, status="open",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


# ---------------------------------------------------------------------------
# POST /api/poams
# ---------------------------------------------------------------------------


class TestCreatePOAM:
    def test_creates_poam(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        res = client.post("/api/poams", json={
            "org_id": org.id, "title": "Remediation Plan",
        }, headers=_auth_header(user))

        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Remediation Plan"
        assert data["status"] == "draft"
        assert data["org_id"] == org.id

    def test_requires_auth(self, client, db):
        org = _create_org(db)
        res = client.post("/api/poams", json={
            "org_id": org.id, "title": "No Auth",
        })
        assert res.status_code == 401

    def test_rejects_viewer_role(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        res = client.post("/api/poams", json={
            "org_id": org.id, "title": "Viewer Attempt",
        }, headers=_auth_header(user))
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/poams
# ---------------------------------------------------------------------------


class TestListPOAMs:
    def test_lists_org_poams(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        _create_poam(db, org.id, "Plan A")
        _create_poam(db, org.id, "Plan B")

        res = client.get("/api/poams", headers=_auth_header(user))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2

    def test_filters_by_status(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        _create_poam(db, org.id, "Draft", status="draft")
        _create_poam(db, org.id, "Active", status="active")

        res = client.get("/api/poams?status=active", headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "Active"

    def test_non_admin_sees_only_own_org(self, client, db):
        org1 = _create_org(db, "Org1")
        org2 = _create_org(db, "Org2")
        user1 = _create_user(db, username="u1", email="u1@t.com", org_id=org1.id, role_names=["compliance_officer"])
        _create_poam(db, org1.id, "Org1 Plan")
        _create_poam(db, org2.id, "Org2 Plan")

        res = client.get("/api/poams", headers=_auth_header(user1))
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "Org1 Plan"


# ---------------------------------------------------------------------------
# GET /api/poams/{id}
# ---------------------------------------------------------------------------


class TestGetPOAM:
    def test_returns_poam_with_items(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)
        _create_item(db, poam.id, "Item 1")
        _create_item(db, poam.id, "Item 2")

        res = client.get(f"/api/poams/{poam.id}", headers=_auth_header(user))
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Test POA&M"
        assert len(data["items"]) == 2

    def test_404_for_missing(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        res = client.get("/api/poams/nonexistent", headers=_auth_header(user))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/poams/{id}
# ---------------------------------------------------------------------------


class TestUpdatePOAM:
    def test_updates_title(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)

        res = client.patch(f"/api/poams/{poam.id}", json={
            "title": "Updated Title",
        }, headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["title"] == "Updated Title"

    def test_rejects_completed(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id, status="completed")

        res = client.patch(f"/api/poams/{poam.id}", json={
            "title": "Nope",
        }, headers=_auth_header(user))
        assert res.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /api/poams/{id}
# ---------------------------------------------------------------------------


class TestDeletePOAM:
    def test_deletes_draft(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)

        res = client.delete(f"/api/poams/{poam.id}", headers=_auth_header(user))
        assert res.status_code == 204

    def test_rejects_active(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id, status="active")

        res = client.delete(f"/api/poams/{poam.id}", headers=_auth_header(user))
        assert res.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/poams/{id}/activate + /complete
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_activate(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)

        res = client.post(f"/api/poams/{poam.id}/activate", headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["status"] == "active"

    def test_complete(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id, status="active")

        res = client.post(f"/api/poams/{poam.id}/complete", headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

    def test_invalid_transition(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)  # draft

        res = client.post(f"/api/poams/{poam.id}/complete", headers=_auth_header(user))
        assert res.status_code == 409


# ---------------------------------------------------------------------------
# Item endpoints
# ---------------------------------------------------------------------------


class TestItemEndpoints:
    def test_add_item(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)

        res = client.post(f"/api/poams/{poam.id}/items", json={
            "milestone": "Deploy MFA",
            "practice_id": "AC.L2-3.1.5",
        }, headers=_auth_header(user))
        assert res.status_code == 201
        data = res.json()
        assert data["milestone"] == "Deploy MFA"
        assert data["status"] == "open"

    def test_update_item(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)
        item = _create_item(db, poam.id)

        res = client.patch(f"/api/poams/{poam.id}/items/{item.id}", json={
            "milestone": "Updated Milestone",
            "status": "in_progress",
        }, headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["milestone"] == "Updated Milestone"
        assert res.json()["status"] == "in_progress"

    def test_remove_item(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        poam = _create_poam(db, org.id)
        item = _create_item(db, poam.id)

        res = client.delete(f"/api/poams/{poam.id}/items/{item.id}", headers=_auth_header(user))
        assert res.status_code == 204


# ---------------------------------------------------------------------------
# POST /api/poams/generate/{assessment_id}
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_generates_from_findings(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        _create_finding(db, assessment.id, "Finding A")
        _create_finding(db, assessment.id, "Finding B")
        poam = _create_poam(db, org.id, assessment_id=assessment.id)

        res = client.post(
            f"/api/poams/generate/{assessment.id}?poam_id={poam.id}",
            headers=_auth_header(user),
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2

    def test_empty_when_no_findings(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        poam = _create_poam(db, org.id, assessment_id=assessment.id)

        res = client.post(
            f"/api/poams/generate/{assessment.id}?poam_id={poam.id}",
            headers=_auth_header(user),
        )
        assert res.status_code == 200
        assert res.json() == []
