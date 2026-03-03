"""Tests for report API endpoints."""

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.finding import Finding
from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_org(db: Session, name: str = "Acme Corp") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _create_user(
    db: Session,
    org_id: str | None = None,
    role_names: list[str] | None = None,
) -> User:
    user = User(
        username="reportuser",
        email="report@example.com",
        password_hash=hash_password("password123"),
        org_id=org_id,
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


def _auth(user: User) -> dict:
    token = create_access_token(user.id, [r.name for r in user.roles])
    return {"Authorization": f"Bearer {token}"}


def _seed_assessment_with_data(db: Session, org_id: str) -> Assessment:
    """Create a full assessment with domain, practices, evals, findings."""
    domain = CMMCDomain(domain_id="AC", name="Access Control")
    db.add(domain)
    db.flush()

    p1 = CMMCPractice(practice_id="AC.L1-3.1.1", domain_ref="AC", level=1, title="Auth Access")
    p2 = CMMCPractice(practice_id="AC.L1-3.1.2", domain_ref="AC", level=1, title="Transaction Control")
    db.add_all([p1, p2])
    db.flush()

    a = Assessment(
        org_id=org_id,
        title="Q1 Assessment",
        target_level=1,
        assessment_type="self",
        status="completed",
        overall_score=50.0,
        sprs_score=85,
    )
    db.add(a)
    db.flush()

    db.add(AssessmentPractice(assessment_id=a.id, practice_id="AC.L1-3.1.1", status="met"))
    db.add(AssessmentPractice(assessment_id=a.id, practice_id="AC.L1-3.1.2", status="not_met"))
    db.add(Finding(
        assessment_id=a.id,
        finding_type="observation",
        severity="high",
        title="Gap found",
        status="open",
    ))

    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# GET /api/reports/assessment/{id}?format=csv
# ---------------------------------------------------------------------------


class TestAssessmentReportCSV:
    def test_returns_csv(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment_with_data(db, org.id)

        resp = client.get(
            f"/api/reports/assessment/{a.id}?format=csv", headers=_auth(user)
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in resp.headers["content-disposition"]
        assert b"AC.L1-3.1.1" in resp.content

    def test_default_format_is_csv(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment_with_data(db, org.id)

        resp = client.get(
            f"/api/reports/assessment/{a.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_not_found(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        resp = client.get(
            "/api/reports/assessment/nonexistent?format=csv", headers=_auth(user)
        )
        assert resp.status_code == 404

    def test_unauthenticated(self, client):
        resp = client.get("/api/reports/assessment/fake?format=csv")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/reports/assessment/{id}?format=pdf
# ---------------------------------------------------------------------------


class TestAssessmentReportPDF:
    def test_returns_pdf(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment_with_data(db, org.id)

        resp = client.get(
            f"/api/reports/assessment/{a.id}?format=pdf", headers=_auth(user)
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"

    def test_not_found(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        resp = client.get(
            "/api/reports/assessment/nonexistent?format=pdf", headers=_auth(user)
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/reports/assessment/{id}?format=invalid
# ---------------------------------------------------------------------------


class TestInvalidFormat:
    def test_rejects_invalid_format(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment_with_data(db, org.id)

        resp = client.get(
            f"/api/reports/assessment/{a.id}?format=xlsx", headers=_auth(user)
        )
        assert resp.status_code == 422  # validation error from Query enum


# ---------------------------------------------------------------------------
# GET /api/reports/sprs/{org_id}
# ---------------------------------------------------------------------------


class TestSprsReport:
    def test_returns_sprs_csv(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["system_admin"])
        _seed_assessment_with_data(db, org.id)

        resp = client.get(
            f"/api/reports/sprs/{org.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert b"SPRS" in resp.content or b"sprs" in resp.content.lower()

    def test_empty_org(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["system_admin"])

        resp = client.get(
            f"/api/reports/sprs/{org.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        # Should still return a valid CSV with headers

    def test_unauthenticated(self, client):
        resp = client.get("/api/reports/sprs/fake")
        assert resp.status_code == 401
