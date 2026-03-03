"""Tests for practice evaluation API endpoints."""

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


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _token_for(user: User) -> str:
    return create_access_token(user.id, [r.name for r in user.roles])


def _create_org(db: Session, name: str = "Acme Corp") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _seed_practices(db: Session) -> None:
    """Seed two domains with practices."""
    ac = db.query(CMMCDomain).filter_by(domain_id="AC").first()
    if not ac:
        ac = CMMCDomain(domain_id="AC", name="Access Control")
        db.add(ac)
    ia = db.query(CMMCDomain).filter_by(domain_id="IA").first()
    if not ia:
        ia = CMMCDomain(domain_id="IA", name="Identification and Authentication")
        db.add(ia)
    db.flush()

    for pid, dom, lvl, title in [
        ("AC.L1-3.1.1", "AC", 1, "Limit access"),
        ("AC.L1-3.1.2", "AC", 1, "Limit transactions"),
        ("IA.L1-3.5.1", "IA", 1, "Identify users"),
    ]:
        if not db.query(CMMCPractice).filter_by(practice_id=pid).first():
            db.add(CMMCPractice(practice_id=pid, domain_ref=dom, level=lvl, title=title))
    db.commit()


def _create_assessment(
    db: Session,
    org_id: str,
    status: str = "in_progress",
) -> Assessment:
    """Create an assessment and its practice records directly."""
    assessment = Assessment(
        org_id=org_id,
        title="Test Assessment",
        target_level=1,
        assessment_type="self",
        status=status,
    )
    db.add(assessment)
    db.flush()

    # Add assessment practices for all seeded L1 practices
    for p in db.query(CMMCPractice).filter(CMMCPractice.level <= 1).all():
        db.add(AssessmentPractice(
            assessment_id=assessment.id,
            practice_id=p.practice_id,
            status="not_evaluated",
        ))

    db.commit()
    db.refresh(assessment)
    return assessment


# ---------------------------------------------------------------------------
# GET /api/assessments/{id}/practices
# ---------------------------------------------------------------------------

class TestListPracticeEvaluations:
    def test_list_all(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3  # AC.L1-3.1.1, AC.L1-3.1.2, IA.L1-3.5.1

    def test_filter_by_status(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        # Evaluate one practice directly in DB
        ap = db.query(AssessmentPractice).filter_by(
            assessment_id=assessment.id, practice_id="AC.L1-3.1.1"
        ).first()
        ap.status = "met"
        db.commit()

        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            f"/api/assessments/{assessment.id}/practices?status=met",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["practice_id"] == "AC.L1-3.1.1"

    def test_filter_by_domain(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices?domain=AC",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        for p in data:
            assert p["practice_id"].startswith("AC.")

    def test_assessment_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments/nonexistent/practices",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        _seed_practices(db)
        assessment = _create_assessment(db, org2.id)
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_system_admin_any_org(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        admin = _create_user(db, username="admin", email="admin@example.com", role_names=["system_admin"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices",
            headers=_auth_header(_token_for(admin)),
        )
        assert resp.status_code == 200

    def test_unauthenticated(self, client):
        resp = client.get("/api/assessments/someid/practices")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/assessments/{id}/practices/{practice_id}
# ---------------------------------------------------------------------------

class TestGetPracticeEvaluation:
    def test_get_success(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["practice_id"] == "AC.L1-3.1.1"
        assert data["status"] == "not_evaluated"
        assert data["assessment_id"] == assessment.id

    def test_assessment_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.get(
            "/api/assessments/nonexistent/practices/AC.L1-3.1.1",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_practice_not_found(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices/NONEXIST",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        _seed_practices(db)
        assessment = _create_assessment(db, org2.id)
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])

        resp = client.get(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_unauthenticated(self, client):
        resp = client.get("/api/assessments/someid/practices/AC.L1-3.1.1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/assessments/{id}/practices/{practice_id}
# ---------------------------------------------------------------------------

class TestUpdatePracticeEvaluation:
    def test_update_status(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "met"

    def test_update_score_and_notes(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["assessor"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"score": 0.75, "assessor_notes": "Partial compliance"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 0.75
        assert data["assessor_notes"] == "Partial compliance"

    def test_update_all_fields(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "not_met", "score": 0.0, "assessor_notes": "No evidence"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_met"
        assert data["score"] == 0.0
        assert data["assessor_notes"] == "No evidence"

    def test_rejects_when_draft(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id, status="draft")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_rejects_when_completed(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id, status="completed")
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_assessment_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        resp = client.patch(
            "/api/assessments/nonexistent/practices/AC.L1-3.1.1",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_practice_not_found(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/NONEXIST",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_invalid_status(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "invalid_status"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 422

    def test_invalid_score(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"score": 1.5},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 422

    def test_other_org_forbidden(self, client, db):
        org1 = _create_org(db, name="Org A")
        org2 = _create_org(db, name="Org B")
        _seed_practices(db)
        assessment = _create_assessment(db, org2.id)
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_forbidden_viewer(self, client, db):
        org = _create_org(db)
        _seed_practices(db)
        assessment = _create_assessment(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        resp = client.patch(
            f"/api/assessments/{assessment.id}/practices/AC.L1-3.1.1",
            json={"status": "met"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_unauthenticated(self, client):
        resp = client.patch(
            "/api/assessments/someid/practices/AC.L1-3.1.1",
            json={"status": "met"},
        )
        assert resp.status_code == 401
