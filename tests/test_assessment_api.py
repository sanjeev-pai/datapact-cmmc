"""Tests for assessment API endpoints."""

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
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


def _seed_practices(db: Session, count: int = 3, level: int = 1) -> list[CMMCPractice]:
    """Seed a domain and practices for testing."""
    domain = db.query(CMMCDomain).filter(CMMCDomain.domain_id == "AC").first()
    if not domain:
        domain = CMMCDomain(domain_id="AC", name="Access Control")
        db.add(domain)
        db.flush()

    practices = []
    for i in range(count):
        pid = f"AC.L{level}-3.1.{i + 1}"
        p = db.query(CMMCPractice).filter(CMMCPractice.practice_id == pid).first()
        if not p:
            p = CMMCPractice(
                practice_id=pid,
                domain_ref="AC",
                level=level,
                title=f"Practice {pid}",
            )
            db.add(p)
        practices.append(p)

    db.commit()
    return practices


def _create_assessment(
    db: Session,
    org_id: str,
    title: str = "Test Assessment",
    target_level: int = 1,
    assessment_type: str = "self",
    status: str = "draft",
) -> Assessment:
    """Create an assessment directly in the DB for test setup."""
    assessment = Assessment(
        org_id=org_id,
        title=title,
        target_level=target_level,
        assessment_type=assessment_type,
        status=status,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


# ---------------------------------------------------------------------------
# POST /api/assessments
# ---------------------------------------------------------------------------

class TestCreateAssessment:
    def test_create_success(self, client, db):
        org = _create_org(db)
        _seed_practices(db, count=3, level=1)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org.id,
                "title": "Q1 Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Q1 Assessment"
        assert data["status"] == "draft"
        assert data["target_level"] == 1
        assert data["org_id"] == org.id
        assert "id" in data

    def test_create_with_lead_assessor(self, client, db):
        org = _create_org(db)
        _seed_practices(db, count=2, level=1)
        assessor = _create_user(db, username="assessor", email="a@example.com", org_id=org.id, role_names=["assessor"])
        officer = _create_user(db, username="officer", email="o@example.com", org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org.id,
                "title": "Assessed",
                "target_level": 1,
                "assessment_type": "third_party",
                "lead_assessor_id": assessor.id,
            },
            headers=_auth_header(_token_for(officer)),
        )
        assert resp.status_code == 201
        assert resp.json()["lead_assessor_id"] == assessor.id

    def test_create_populates_practices(self, client, db):
        org = _create_org(db)
        _seed_practices(db, count=3, level=1)
        user = _create_user(db, org_id=org.id, role_names=["org_admin"])
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org.id,
                "title": "With Practices",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 201
        assessment_id = resp.json()["id"]
        count = db.query(AssessmentPractice).filter_by(assessment_id=assessment_id).count()
        assert count == 3

    def test_create_forbidden_viewer(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org.id,
                "title": "Nope",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_create_unauthenticated(self, client):
        resp = client.post(
            "/api/assessments",
            json={"org_id": "x", "title": "No", "target_level": 1, "assessment_type": "self"},
        )
        assert resp.status_code == 401

    def test_create_invalid_level(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org.id,
                "title": "Bad",
                "target_level": 5,
                "assessment_type": "self",
            },
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 422

    def test_create_invalid_type(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org.id,
                "title": "Bad",
                "target_level": 1,
                "assessment_type": "invalid",
            },
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 422

    def test_create_missing_title(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            "/api/assessments",
            json={"org_id": org.id, "target_level": 1, "assessment_type": "self"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/assessments
# ---------------------------------------------------------------------------

class TestListAssessments:
    def test_list_own_org(self, client, db):
        org = _create_org(db)
        _create_assessment(db, org_id=org.id, title="A1")
        _create_assessment(db, org_id=org.id, title="A2")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_filter_by_status(self, client, db):
        org = _create_org(db)
        _create_assessment(db, org_id=org.id, title="Draft", status="draft")
        _create_assessment(db, org_id=org.id, title="Active", status="in_progress")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments?status=draft",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "draft"

    def test_list_filter_by_level(self, client, db):
        org = _create_org(db)
        _create_assessment(db, org_id=org.id, title="L1", target_level=1)
        _create_assessment(db, org_id=org.id, title="L2", target_level=2)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments?target_level=2",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["target_level"] == 2

    def test_list_empty(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_system_admin_with_org_filter(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        _create_assessment(db, org_id=org1.id, title="A1")
        _create_assessment(db, org_id=org2.id, title="B1")
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.get(
            f"/api/assessments?org_id={org1.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "A1"

    def test_list_unauthenticated(self, client):
        resp = client.get("/api/assessments")
        assert resp.status_code == 401

    def test_list_user_without_org(self, client, db):
        user = _create_user(db, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/assessments/{id}
# ---------------------------------------------------------------------------

class TestGetAssessment:
    def test_get_success(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, title="Detail Test")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Detail Test"
        assert data["id"] == assessment.id

    def test_get_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments/nonexistent",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_get_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        assessment = _create_assessment(db, org_id=org2.id, title="Other Org")
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])
        resp = client.get(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_get_system_admin_any_org(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id)
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])
        resp = client.get(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200

    def test_get_unauthenticated(self, client):
        resp = client.get("/api/assessments/someid")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/assessments/{id}
# ---------------------------------------------------------------------------

class TestUpdateAssessment:
    def test_update_title(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, title="Old Title")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.patch(
            f"/api/assessments/{assessment.id}",
            json={"title": "New Title"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"

    def test_update_multiple_fields(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id)
        user = _create_user(db, org_id=org.id, role_names=["org_admin"])
        resp = client.patch(
            f"/api/assessments/{assessment.id}",
            json={"title": "Updated", "assessment_type": "third_party"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated"
        assert data["assessment_type"] == "third_party"

    def test_update_completed_rejected(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="completed")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.patch(
            f"/api/assessments/{assessment.id}",
            json={"title": "Nope"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_update_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.patch(
            "/api/assessments/nonexistent",
            json={"title": "Nope"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_update_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        assessment = _create_assessment(db, org_id=org2.id)
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])
        resp = client.patch(
            f"/api/assessments/{assessment.id}",
            json={"title": "Hacked"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_update_forbidden_viewer(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.patch(
            f"/api/assessments/{assessment.id}",
            json={"title": "Nope"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_update_unauthenticated(self, client):
        resp = client.patch("/api/assessments/someid", json={"title": "X"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/assessments/{id}
# ---------------------------------------------------------------------------

class TestDeleteAssessment:
    def test_delete_draft(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="draft")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.delete(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 204
        assert db.query(Assessment).filter_by(id=assessment.id).first() is None

    def test_delete_non_draft_rejected(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="in_progress")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.delete(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_delete_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.delete(
            "/api/assessments/nonexistent",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_delete_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        assessment = _create_assessment(db, org_id=org2.id)
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])
        resp = client.delete(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_delete_forbidden_viewer(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.delete(
            f"/api/assessments/{assessment.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_delete_unauthenticated(self, client):
        resp = client.delete("/api/assessments/someid")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/assessments/{id}/start
# ---------------------------------------------------------------------------

class TestStartAssessment:
    def test_start_draft(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="draft")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/start",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None

    def test_start_non_draft_rejected(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="in_progress")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/start",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_start_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            "/api/assessments/nonexistent/start",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_start_forbidden_viewer(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="draft")
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/start",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_start_unauthenticated(self, client):
        resp = client.post("/api/assessments/someid/start")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/assessments/{id}/submit
# ---------------------------------------------------------------------------

class TestSubmitAssessment:
    def test_submit_in_progress(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="in_progress")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/submit",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "under_review"

    def test_submit_draft_rejected(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="draft")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/submit",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_submit_unauthenticated(self, client):
        resp = client.post("/api/assessments/someid/submit")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/assessments/{id}/complete
# ---------------------------------------------------------------------------

class TestCompleteAssessment:
    def test_complete_under_review(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="under_review")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/complete",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_complete_draft_rejected(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org_id=org.id, status="draft")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.post(
            f"/api/assessments/{assessment.id}/complete",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_complete_unauthenticated(self, client):
        resp = client.post("/api/assessments/someid/complete")
        assert resp.status_code == 401
