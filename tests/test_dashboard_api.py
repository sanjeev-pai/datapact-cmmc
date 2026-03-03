"""Tests for dashboard API endpoints."""

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
        username="dashuser",
        email="dash@example.com",
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


def _seed_domain(db: Session, domain_id: str, name: str) -> CMMCDomain:
    d = CMMCDomain(domain_id=domain_id, name=name)
    db.add(d)
    db.flush()
    return d


def _seed_practice(
    db: Session, practice_id: str, domain_ref: str, level: int = 1
) -> CMMCPractice:
    p = CMMCPractice(
        practice_id=practice_id,
        domain_ref=domain_ref,
        level=level,
        title=f"Practice {practice_id}",
    )
    db.add(p)
    db.flush()
    return p


def _seed_assessment(
    db: Session,
    org_id: str,
    *,
    title: str = "Test Assessment",
    target_level: int = 1,
    status: str = "completed",
    overall_score: float | None = None,
    sprs_score: int | None = None,
) -> Assessment:
    a = Assessment(
        org_id=org_id,
        title=title,
        target_level=target_level,
        assessment_type="self",
        status=status,
        overall_score=overall_score,
        sprs_score=sprs_score,
    )
    db.add(a)
    db.flush()
    return a


def _seed_eval(
    db: Session, assessment_id: str, practice_id: str, status: str = "met"
) -> AssessmentPractice:
    ap = AssessmentPractice(
        assessment_id=assessment_id,
        practice_id=practice_id,
        status=status,
    )
    db.add(ap)
    db.flush()
    return ap


def _seed_finding(
    db: Session,
    assessment_id: str,
    *,
    severity: str = "high",
    status: str = "open",
) -> Finding:
    f = Finding(
        assessment_id=assessment_id,
        finding_type="observation",
        severity=severity,
        title=f"{severity} finding",
        status=status,
    )
    db.add(f)
    db.flush()
    return f


# ---------------------------------------------------------------------------
# GET /api/dashboard/summary
# ---------------------------------------------------------------------------


class TestDashboardSummary:
    def test_returns_compliance_summary(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC", level=1)
        _seed_practice(db, "AC.L1-3.1.2", "AC", level=1)
        a = _seed_assessment(db, org.id, target_level=1, status="completed")
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        _seed_eval(db, a.id, "AC.L1-3.1.2", "not_met")
        db.commit()

        resp = client.get("/api/dashboard/summary", headers=_auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["level_1"] == 50.0
        assert data["level_2"] is None
        assert data["level_3"] is None

    def test_unauthenticated(self, client):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 401

    def test_no_org_returns_empty(self, db, client):
        # User without org_id
        user = _create_user(db, org_id=None)
        resp = client.get("/api/dashboard/summary", headers=_auth(user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["level_1"] is None


# ---------------------------------------------------------------------------
# GET /api/dashboard/domain-compliance/{assessment_id}
# ---------------------------------------------------------------------------


class TestDomainCompliance:
    def test_returns_per_domain_scores(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC")
        a = _seed_assessment(db, org.id, target_level=1)
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        db.commit()

        resp = client.get(
            f"/api/dashboard/domain-compliance/{a.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["domain_id"] == "AC"
        assert data[0]["percentage"] == 100.0

    def test_empty_assessment(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment(db, org.id)
        db.commit()

        resp = client.get(
            f"/api/dashboard/domain-compliance/{a.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client):
        resp = client.get("/api/dashboard/domain-compliance/fake")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/dashboard/sprs-history/{org_id}
# ---------------------------------------------------------------------------


class TestSprsHistory:
    def test_returns_history(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["system_admin"])
        _seed_assessment(db, org.id, title="A1", sprs_score=72, status="completed")
        _seed_assessment(db, org.id, title="A2", sprs_score=95, status="completed")
        db.commit()

        resp = client.get(
            f"/api/dashboard/sprs-history/{org.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"] == 95
        assert len(data["history"]) == 2

    def test_empty_history(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["system_admin"])
        resp = client.get(
            f"/api/dashboard/sprs-history/{org.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"] is None

    def test_unauthenticated(self, client):
        resp = client.get("/api/dashboard/sprs-history/fake")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/dashboard/timeline/{org_id}
# ---------------------------------------------------------------------------


class TestTimeline:
    def test_returns_recent_assessments(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["system_admin"])
        _seed_assessment(db, org.id, title="A1", status="completed")
        _seed_assessment(db, org.id, title="A2", status="in_progress")
        db.commit()

        resp = client.get(
            f"/api/dashboard/timeline/{org.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["title"] == "A2"  # newest first

    def test_respects_limit_param(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["system_admin"])
        for i in range(5):
            _seed_assessment(db, org.id, title=f"A{i}")
        db.commit()

        resp = client.get(
            f"/api/dashboard/timeline/{org.id}?limit=2", headers=_auth(user)
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_unauthenticated(self, client):
        resp = client.get("/api/dashboard/timeline/fake")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/dashboard/findings-summary/{assessment_id}
# ---------------------------------------------------------------------------


class TestFindingsSummary:
    def test_returns_counts(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment(db, org.id)
        _seed_finding(db, a.id, severity="critical", status="open")
        _seed_finding(db, a.id, severity="high", status="closed")
        _seed_finding(db, a.id, severity="high", status="open")
        db.commit()

        resp = client.get(
            f"/api/dashboard/findings-summary/{a.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["by_severity"]["critical"] == 1
        assert data["by_severity"]["high"] == 2
        assert data["by_status"]["open"] == 2
        assert data["by_status"]["closed"] == 1

    def test_no_findings(self, db, client):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id)
        a = _seed_assessment(db, org.id)
        db.commit()

        resp = client.get(
            f"/api/dashboard/findings-summary/{a.id}", headers=_auth(user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_unauthenticated(self, client):
        resp = client.get("/api/dashboard/findings-summary/fake")
        assert resp.status_code == 401
