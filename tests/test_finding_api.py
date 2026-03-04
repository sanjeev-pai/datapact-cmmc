"""Tests for Findings API endpoints."""

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment
from cmmc.models.finding import Finding
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


def _auth_header(user: User) -> dict:
    token = create_access_token(user.id, [r.name for r in user.roles])
    return {"Authorization": f"Bearer {token}"}


def _create_org(db: Session, name: str = "Acme Corp") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _create_assessment(db: Session, org_id: str, status: str = "in_progress") -> Assessment:
    a = Assessment(
        org_id=org_id,
        title="L2 Assessment",
        target_level=2,
        assessment_type="self",
        status=status,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _create_finding(
    db: Session,
    assessment_id: str,
    title: str = "Test Finding",
    finding_type: str = "deficiency",
    severity: str = "high",
    status: str = "open",
) -> Finding:
    f = Finding(
        assessment_id=assessment_id,
        practice_id="AC.L2-3.1.1",
        finding_type=finding_type,
        severity=severity,
        title=title,
        status=status,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


# ---------------------------------------------------------------------------
# POST /api/findings
# ---------------------------------------------------------------------------


class TestCreateFinding:
    def test_creates_finding(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)

        res = client.post("/api/findings", json={
            "assessment_id": assessment.id,
            "practice_id": "AC.L2-3.1.1",
            "finding_type": "deficiency",
            "severity": "high",
            "title": "Missing MFA",
            "description": "MFA not implemented for privileged accounts",
        }, headers=_auth_header(user))

        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Missing MFA"
        assert data["finding_type"] == "deficiency"
        assert data["severity"] == "high"
        assert data["status"] == "open"
        assert data["assessment_id"] == assessment.id
        assert data["practice_id"] == "AC.L2-3.1.1"

    def test_creates_finding_without_practice(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["assessor"])
        assessment = _create_assessment(db, org.id)

        res = client.post("/api/findings", json={
            "assessment_id": assessment.id,
            "finding_type": "observation",
            "severity": "low",
            "title": "General observation",
        }, headers=_auth_header(user))

        assert res.status_code == 201
        assert res.json()["practice_id"] is None

    def test_requires_auth(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org.id)

        res = client.post("/api/findings", json={
            "assessment_id": assessment.id,
            "finding_type": "deficiency",
            "severity": "high",
            "title": "No Auth",
        })
        assert res.status_code == 401

    def test_rejects_viewer_role(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])
        assessment = _create_assessment(db, org.id)

        res = client.post("/api/findings", json={
            "assessment_id": assessment.id,
            "finding_type": "deficiency",
            "severity": "high",
            "title": "Viewer Attempt",
        }, headers=_auth_header(user))
        assert res.status_code == 403

    def test_rejects_other_org(self, client, db):
        org1 = _create_org(db, "Org1")
        org2 = _create_org(db, "Org2")
        user = _create_user(db, org_id=org1.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org2.id)

        res = client.post("/api/findings", json={
            "assessment_id": assessment.id,
            "finding_type": "deficiency",
            "severity": "high",
            "title": "Cross-org attempt",
        }, headers=_auth_header(user))
        assert res.status_code == 403

    def test_rejects_invalid_assessment(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        res = client.post("/api/findings", json={
            "assessment_id": "nonexistent",
            "finding_type": "deficiency",
            "severity": "high",
            "title": "Bad Assessment",
        }, headers=_auth_header(user))
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/findings
# ---------------------------------------------------------------------------


class TestListFindings:
    def test_lists_org_findings(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        _create_finding(db, assessment.id, "Finding A")
        _create_finding(db, assessment.id, "Finding B")

        res = client.get("/api/findings", headers=_auth_header(user))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2

    def test_filters_by_assessment(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        a1 = _create_assessment(db, org.id)
        a2 = _create_assessment(db, org.id)
        _create_finding(db, a1.id, "A1 Finding")
        _create_finding(db, a2.id, "A2 Finding")

        res = client.get(f"/api/findings?assessment_id={a1.id}", headers=_auth_header(user))
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "A1 Finding"

    def test_filters_by_type(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        _create_finding(db, assessment.id, "Deficiency", finding_type="deficiency")
        _create_finding(db, assessment.id, "Observation", finding_type="observation")

        res = client.get("/api/findings?type=observation", headers=_auth_header(user))
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "Observation"

    def test_filters_by_severity(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        _create_finding(db, assessment.id, "High", severity="high")
        _create_finding(db, assessment.id, "Low", severity="low")

        res = client.get("/api/findings?severity=low", headers=_auth_header(user))
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "Low"

    def test_filters_by_status(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        _create_finding(db, assessment.id, "Open", status="open")
        _create_finding(db, assessment.id, "Resolved", status="resolved")

        res = client.get("/api/findings?status=resolved", headers=_auth_header(user))
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "Resolved"

    def test_non_admin_sees_only_own_org(self, client, db):
        org1 = _create_org(db, "Org1")
        org2 = _create_org(db, "Org2")
        user1 = _create_user(db, username="u1", email="u1@t.com", org_id=org1.id, role_names=["compliance_officer"])
        a1 = _create_assessment(db, org1.id)
        a2 = _create_assessment(db, org2.id)
        _create_finding(db, a1.id, "Org1 Finding")
        _create_finding(db, a2.id, "Org2 Finding")

        res = client.get("/api/findings", headers=_auth_header(user1))
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["title"] == "Org1 Finding"


# ---------------------------------------------------------------------------
# GET /api/findings/{id}
# ---------------------------------------------------------------------------


class TestGetFinding:
    def test_returns_finding(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id, "My Finding")

        res = client.get(f"/api/findings/{finding.id}", headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["title"] == "My Finding"

    def test_404_for_missing(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        res = client.get("/api/findings/nonexistent", headers=_auth_header(user))
        assert res.status_code == 404

    def test_rejects_other_org(self, client, db):
        org1 = _create_org(db, "Org1")
        org2 = _create_org(db, "Org2")
        user1 = _create_user(db, username="u1", email="u1@t.com", org_id=org1.id, role_names=["compliance_officer"])
        a2 = _create_assessment(db, org2.id)
        finding = _create_finding(db, a2.id, "Other Org Finding")

        res = client.get(f"/api/findings/{finding.id}", headers=_auth_header(user1))
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/findings/{id}
# ---------------------------------------------------------------------------


class TestUpdateFinding:
    def test_updates_fields(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id)

        res = client.patch(f"/api/findings/{finding.id}", json={
            "title": "Updated Title",
            "severity": "low",
        }, headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["title"] == "Updated Title"
        assert res.json()["severity"] == "low"

    def test_updates_status(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id)

        res = client.patch(f"/api/findings/{finding.id}", json={
            "status": "resolved",
        }, headers=_auth_header(user))
        assert res.status_code == 200
        assert res.json()["status"] == "resolved"

    def test_rejects_resolved_update(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id, status="resolved")

        res = client.patch(f"/api/findings/{finding.id}", json={
            "title": "Nope",
        }, headers=_auth_header(user))
        assert res.status_code == 409

    def test_requires_auth(self, client, db):
        org = _create_org(db)
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id)

        res = client.patch(f"/api/findings/{finding.id}", json={"title": "No Auth"})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/findings/{id}
# ---------------------------------------------------------------------------


class TestDeleteFinding:
    def test_deletes_open_finding(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id)

        res = client.delete(f"/api/findings/{finding.id}", headers=_auth_header(user))
        assert res.status_code == 204

        # Verify deleted
        res = client.get(f"/api/findings/{finding.id}", headers=_auth_header(user))
        assert res.status_code == 404

    def test_rejects_non_open_delete(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])
        assessment = _create_assessment(db, org.id)
        finding = _create_finding(db, assessment.id, status="resolved")

        res = client.delete(f"/api/findings/{finding.id}", headers=_auth_header(user))
        assert res.status_code == 409

    def test_404_for_missing(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        res = client.delete("/api/findings/nonexistent", headers=_auth_header(user))
        assert res.status_code == 404

    def test_rejects_other_org(self, client, db):
        org1 = _create_org(db, "Org1")
        org2 = _create_org(db, "Org2")
        user1 = _create_user(db, username="u1", email="u1@t.com", org_id=org1.id, role_names=["compliance_officer"])
        a2 = _create_assessment(db, org2.id)
        finding = _create_finding(db, a2.id)

        res = client.delete(f"/api/findings/{finding.id}", headers=_auth_header(user1))
        assert res.status_code == 403
