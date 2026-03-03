"""Tests for evidence API endpoints."""

import io

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password
from cmmc.services.evidence_service import upload_evidence, review_evidence


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


def _seed_assessment_practice(db: Session, org_id: str) -> AssessmentPractice:
    """Create domain, practice, assessment, and assessment_practice."""
    domain = db.query(CMMCDomain).filter(CMMCDomain.domain_id == "AC").first()
    if not domain:
        domain = CMMCDomain(domain_id="AC", name="Access Control")
        db.add(domain)
        db.flush()

    practice = db.query(CMMCPractice).filter(CMMCPractice.practice_id == "AC.L1-3.1.1").first()
    if not practice:
        practice = CMMCPractice(
            practice_id="AC.L1-3.1.1",
            domain_ref="AC",
            level=1,
            title="Limit access",
        )
        db.add(practice)
        db.flush()

    assessment = Assessment(
        org_id=org_id,
        title="Test Assessment",
        target_level=1,
        assessment_type="self",
        status="in_progress",
    )
    db.add(assessment)
    db.flush()

    ap = AssessmentPractice(
        assessment_id=assessment.id,
        practice_id="AC.L1-3.1.1",
        status="not_evaluated",
    )
    db.add(ap)
    db.commit()
    db.refresh(ap)
    return ap


# ---------------------------------------------------------------------------
# POST /api/evidence
# ---------------------------------------------------------------------------


class TestUploadEvidence:
    def test_upload_with_file(self, client, db, tmp_path):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.post(
            "/api/evidence",
            data={
                "assessment_practice_id": ap.id,
                "title": "SSP Document",
                "description": "System security plan",
            },
            files={"file": ("ssp.pdf", io.BytesIO(b"PDF content"), "application/pdf")},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "SSP Document"
        assert data["description"] == "System security plan"
        assert data["file_name"] == "ssp.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["review_status"] == "pending"

    def test_upload_without_file(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.post(
            "/api/evidence",
            data={
                "assessment_practice_id": ap.id,
                "title": "Manual Note",
            },
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Manual Note"
        assert data["file_name"] is None

    def test_upload_unauthenticated(self, client):
        resp = client.post(
            "/api/evidence",
            data={"assessment_practice_id": "x", "title": "No auth"},
        )
        assert resp.status_code == 401

    def test_upload_forbidden_viewer(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        resp = client.post(
            "/api/evidence",
            data={"assessment_practice_id": ap.id, "title": "Nope"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_upload_invalid_practice(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.post(
            "/api/evidence",
            data={"assessment_practice_id": "nonexistent", "title": "Bad ref"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/evidence
# ---------------------------------------------------------------------------


class TestListEvidence:
    def test_list_all(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 1")
        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 2")

        resp = client.get(
            "/api/evidence",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_with_filters(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 1")

        resp = client.get(
            f"/api/evidence?assessment_practice_id={ap.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_unauthenticated(self, client):
        resp = client.get("/api/evidence")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/evidence/{id}
# ---------------------------------------------------------------------------


class TestGetEvidence:
    def test_get_success(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="My Doc")

        resp = client.get(
            f"/api/evidence/{ev.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "My Doc"

    def test_get_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        resp = client.get(
            "/api/evidence/nonexistent",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/evidence/{id}/download
# ---------------------------------------------------------------------------


class TestDownloadEvidence:
    def test_download_success(self, client, db, tmp_path):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        ev = upload_evidence(
            db,
            assessment_practice_id=ap.id,
            title="Downloadable",
            file_content=b"hello world",
            file_name="test.txt",
            mime_type="text/plain",
            upload_dir=str(tmp_path),
        )

        resp = client.get(
            f"/api/evidence/{ev.id}/download",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.content == b"hello world"
        assert "test.txt" in resp.headers.get("content-disposition", "")

    def test_download_no_file(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="No file")

        resp = client.get(
            f"/api/evidence/{ev.id}/download",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404

    def test_download_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        resp = client.get(
            "/api/evidence/nonexistent/download",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/evidence/{id}
# ---------------------------------------------------------------------------


class TestDeleteEvidence:
    def test_delete_pending(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="To delete")

        resp = client.delete(
            f"/api/evidence/{ev.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 204

    def test_delete_reviewed_fails(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Reviewed")
        review_evidence(db, ev.id, reviewer_id=user.id, review_status="accepted")

        resp = client.delete(
            f"/api/evidence/{ev.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_delete_forbidden_viewer(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Can't delete")

        resp = client.delete(
            f"/api/evidence/{ev.id}",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_delete_unauthenticated(self, client):
        resp = client.delete("/api/evidence/someid")
        assert resp.status_code == 401

    def test_delete_not_found(self, client, db):
        org = _create_org(db)
        user = _create_user(db, org_id=org.id, role_names=["compliance_officer"])

        resp = client.delete(
            "/api/evidence/nonexistent",
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/evidence/{id}/review
# ---------------------------------------------------------------------------


class TestReviewEvidence:
    def test_accept(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["assessor"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="To review")

        resp = client.post(
            f"/api/evidence/{ev.id}/review",
            json={"review_status": "accepted"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "accepted"
        assert data["reviewer_id"] == user.id
        assert data["reviewed_at"] is not None

    def test_reject(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["assessor"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="To reject")

        resp = client.post(
            f"/api/evidence/{ev.id}/review",
            json={"review_status": "rejected"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "rejected"

    def test_review_already_reviewed(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["assessor"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Already done")
        review_evidence(db, ev.id, reviewer_id=user.id, review_status="accepted")

        resp = client.post(
            f"/api/evidence/{ev.id}/review",
            json={"review_status": "rejected"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 409

    def test_review_invalid_status(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["assessor"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Bad status")

        resp = client.post(
            f"/api/evidence/{ev.id}/review",
            json={"review_status": "pending"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 422

    def test_review_forbidden_viewer(self, client, db):
        org = _create_org(db)
        ap = _seed_assessment_practice(db, org.id)
        user = _create_user(db, org_id=org.id, role_names=["viewer"])

        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Nope")

        resp = client.post(
            f"/api/evidence/{ev.id}/review",
            json={"review_status": "accepted"},
            headers=_auth_header(_token_for(user)),
        )
        assert resp.status_code == 403

    def test_review_unauthenticated(self, client):
        resp = client.post(
            "/api/evidence/someid/review",
            json={"review_status": "accepted"},
        )
        assert resp.status_code == 401
