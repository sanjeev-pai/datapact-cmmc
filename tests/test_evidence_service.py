"""Tests for evidence service."""

import os

import pytest
from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.organization import Organization
from cmmc.models.user import User
from cmmc.services.evidence_service import (
    delete_evidence,
    get_evidence,
    list_evidence,
    review_evidence,
    upload_evidence,
)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_org(db: Session) -> Organization:
    org = Organization(name="Test Org")
    db.add(org)
    db.flush()
    return org


def _seed_user(db: Session, org: Organization) -> User:
    user = User(
        username="assessor1",
        email="assessor@test.com",
        password_hash="fakehash",
        org_id=org.id,
    )
    db.add(user)
    db.flush()
    return user


def _seed_assessment_practice(db: Session) -> tuple[AssessmentPractice, Organization, User]:
    """Create org → user → domain → practice → assessment → assessment_practice."""
    org = _seed_org(db)
    user = _seed_user(db, org)

    domain = CMMCDomain(domain_id="AC", name="Access Control")
    db.add(domain)
    db.flush()

    practice = CMMCPractice(
        practice_id="AC.L1-3.1.1",
        domain_ref="AC",
        level=1,
        title="Limit access",
    )
    db.add(practice)
    db.flush()

    assessment = Assessment(
        org_id=org.id,
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
    db.flush()
    db.commit()

    return ap, org, user


# ---------------------------------------------------------------------------
# upload_evidence
# ---------------------------------------------------------------------------


class TestUploadEvidence:
    def test_upload_with_file(self, db, tmp_path):
        ap, _org, _user = _seed_assessment_practice(db)
        content = b"PDF content here"

        ev = upload_evidence(
            db,
            assessment_practice_id=ap.id,
            title="SSP Document",
            description="System security plan",
            file_content=content,
            file_name="ssp.pdf",
            mime_type="application/pdf",
            upload_dir=str(tmp_path),
        )

        assert ev.id is not None
        assert ev.assessment_practice_id == ap.id
        assert ev.title == "SSP Document"
        assert ev.description == "System security plan"
        assert ev.file_name == "ssp.pdf"
        assert ev.file_size == len(content)
        assert ev.mime_type == "application/pdf"
        assert ev.review_status == "pending"
        assert ev.file_path is not None

        # Verify file written to disk
        assert os.path.exists(ev.file_path)
        with open(ev.file_path, "rb") as f:
            assert f.read() == content

    def test_upload_without_file(self, db):
        ap, _org, _user = _seed_assessment_practice(db)

        ev = upload_evidence(
            db,
            assessment_practice_id=ap.id,
            title="Manual Note",
            description="Verified in person",
        )

        assert ev.title == "Manual Note"
        assert ev.file_path is None
        assert ev.file_name is None
        assert ev.file_size is None

    def test_upload_invalid_assessment_practice(self, db):
        with pytest.raises(NotFoundError):
            upload_evidence(
                db,
                assessment_practice_id="nonexistent",
                title="Bad ref",
            )


# ---------------------------------------------------------------------------
# get_evidence
# ---------------------------------------------------------------------------


class TestGetEvidence:
    def test_get_existing(self, db):
        ap, _org, _user = _seed_assessment_practice(db)
        ev = upload_evidence(
            db,
            assessment_practice_id=ap.id,
            title="Test",
        )

        found = get_evidence(db, ev.id)
        assert found.id == ev.id
        assert found.title == "Test"

    def test_get_not_found(self, db):
        with pytest.raises(NotFoundError):
            get_evidence(db, "nonexistent")


# ---------------------------------------------------------------------------
# list_evidence
# ---------------------------------------------------------------------------


class TestListEvidence:
    def test_list_by_assessment_practice(self, db):
        ap, _org, _user = _seed_assessment_practice(db)
        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 1")
        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 2")

        items, total = list_evidence(db, assessment_practice_id=ap.id)
        assert total == 2
        assert len(items) == 2

    def test_list_by_review_status(self, db):
        ap, _org, user = _seed_assessment_practice(db)
        ev1 = upload_evidence(db, assessment_practice_id=ap.id, title="Doc 1")
        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 2")

        review_evidence(db, ev1.id, reviewer_id=user.id, review_status="accepted")

        items, total = list_evidence(db, review_status="accepted")
        assert total == 1
        assert items[0].review_status == "accepted"

    def test_list_by_assessment_id(self, db):
        ap, _org, _user = _seed_assessment_practice(db)
        upload_evidence(db, assessment_practice_id=ap.id, title="Doc 1")

        items, total = list_evidence(db, assessment_id=ap.assessment_id)
        assert total == 1

    def test_list_empty(self, db):
        items, total = list_evidence(db)
        assert total == 0
        assert items == []


# ---------------------------------------------------------------------------
# delete_evidence
# ---------------------------------------------------------------------------


class TestDeleteEvidence:
    def test_delete_pending(self, db, tmp_path):
        ap, _org, _user = _seed_assessment_practice(db)
        ev = upload_evidence(
            db,
            assessment_practice_id=ap.id,
            title="To Delete",
            file_content=b"data",
            file_name="test.txt",
            upload_dir=str(tmp_path),
        )
        file_path = ev.file_path
        assert os.path.exists(file_path)

        delete_evidence(db, ev.id)

        # DB record gone
        with pytest.raises(NotFoundError):
            get_evidence(db, ev.id)

        # File removed from disk
        assert not os.path.exists(file_path)

    def test_delete_without_file(self, db):
        ap, _org, _user = _seed_assessment_practice(db)
        ev = upload_evidence(
            db,
            assessment_practice_id=ap.id,
            title="Note only",
        )

        delete_evidence(db, ev.id)

        with pytest.raises(NotFoundError):
            get_evidence(db, ev.id)

    def test_delete_reviewed_raises_conflict(self, db):
        ap, _org, user = _seed_assessment_practice(db)
        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Reviewed")
        review_evidence(db, ev.id, reviewer_id=user.id, review_status="accepted")

        with pytest.raises(ConflictError):
            delete_evidence(db, ev.id)

    def test_delete_not_found(self, db):
        with pytest.raises(NotFoundError):
            delete_evidence(db, "nonexistent")


# ---------------------------------------------------------------------------
# review_evidence
# ---------------------------------------------------------------------------


class TestReviewEvidence:
    def test_accept(self, db):
        ap, _org, user = _seed_assessment_practice(db)
        ev = upload_evidence(db, assessment_practice_id=ap.id, title="To review")

        reviewed = review_evidence(db, ev.id, reviewer_id=user.id, review_status="accepted")

        assert reviewed.review_status == "accepted"
        assert reviewed.reviewer_id == user.id
        assert reviewed.reviewed_at is not None

    def test_reject(self, db):
        ap, _org, user = _seed_assessment_practice(db)
        ev = upload_evidence(db, assessment_practice_id=ap.id, title="To reject")

        reviewed = review_evidence(db, ev.id, reviewer_id=user.id, review_status="rejected")

        assert reviewed.review_status == "rejected"

    def test_review_already_reviewed_raises_conflict(self, db):
        ap, _org, user = _seed_assessment_practice(db)
        ev = upload_evidence(db, assessment_practice_id=ap.id, title="Already done")
        review_evidence(db, ev.id, reviewer_id=user.id, review_status="accepted")

        with pytest.raises(ConflictError):
            review_evidence(db, ev.id, reviewer_id=user.id, review_status="rejected")

    def test_review_not_found(self, db):
        _seed_assessment_practice(db)  # ensure tables exist
        with pytest.raises(NotFoundError):
            review_evidence(db, "nonexistent", reviewer_id="u1", review_status="accepted")
