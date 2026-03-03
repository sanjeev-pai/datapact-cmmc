"""Tests for assessment service."""

import pytest
from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.organization import Organization
from cmmc.models.user import User
from cmmc.services.assessment_service import (
    complete_assessment,
    create_assessment,
    delete_assessment,
    get_assessment,
    list_assessments,
    start_assessment,
    submit_assessment,
    update_assessment,
)


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


def _seed_practices(db: Session) -> None:
    """Create domain + practices at levels 1 and 2."""
    domain = CMMCDomain(domain_id="AC", name="Access Control")
    db.add(domain)
    db.flush()

    practices = [
        CMMCPractice(
            practice_id="AC.L1-3.1.1",
            domain_ref="AC",
            level=1,
            title="Limit access to authorized users",
        ),
        CMMCPractice(
            practice_id="AC.L1-3.1.2",
            domain_ref="AC",
            level=1,
            title="Limit access to transactions",
        ),
        CMMCPractice(
            practice_id="AC.L2-3.1.3",
            domain_ref="AC",
            level=2,
            title="Control CUI flow",
        ),
        CMMCPractice(
            practice_id="AC.L2-3.1.4",
            domain_ref="AC",
            level=2,
            title="Separate duties",
        ),
    ]
    db.add_all(practices)
    db.flush()


# ---------------------------------------------------------------------------
# create_assessment
# ---------------------------------------------------------------------------


class TestCreateAssessment:
    def test_creates_with_draft_status(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)

        assessment = create_assessment(
            db,
            org_id=org.id,
            title="L1 Self Assessment",
            target_level=1,
            assessment_type="self",
        )

        assert assessment.id is not None
        assert assessment.status == "draft"
        assert assessment.org_id == org.id
        assert assessment.title == "L1 Self Assessment"

    def test_populates_practices_at_target_level(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)

        assessment = create_assessment(
            db,
            org_id=org.id,
            title="L1 Assessment",
            target_level=1,
            assessment_type="self",
        )

        # Level 1 has 2 practices (AC.L1-3.1.1, AC.L1-3.1.2)
        assert len(assessment.practices) == 2
        practice_ids = {p.practice_id for p in assessment.practices}
        assert "AC.L1-3.1.1" in practice_ids
        assert "AC.L1-3.1.2" in practice_ids

    def test_populates_practices_at_and_below_target_level(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)

        assessment = create_assessment(
            db,
            org_id=org.id,
            title="L2 Assessment",
            target_level=2,
            assessment_type="third_party",
        )

        # Level 2 includes L1 (2) + L2 (2) = 4 practices
        assert len(assessment.practices) == 4

    def test_practices_default_to_not_evaluated(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)

        assessment = create_assessment(
            db,
            org_id=org.id,
            title="L1",
            target_level=1,
            assessment_type="self",
        )

        for ap in assessment.practices:
            assert ap.status == "not_evaluated"

    def test_with_lead_assessor(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        user = _seed_user(db, org)

        assessment = create_assessment(
            db,
            org_id=org.id,
            title="Test",
            target_level=1,
            assessment_type="self",
            lead_assessor_id=user.id,
        )

        assert assessment.lead_assessor_id == user.id


# ---------------------------------------------------------------------------
# get_assessment
# ---------------------------------------------------------------------------


class TestGetAssessment:
    def test_returns_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        created = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )

        result = get_assessment(db, created.id)
        assert result.id == created.id
        assert result.title == "Test"

    def test_raises_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            get_assessment(db, "nonexistent")


# ---------------------------------------------------------------------------
# list_assessments
# ---------------------------------------------------------------------------


class TestListAssessments:
    def test_returns_all_for_org(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        create_assessment(
            db, org_id=org.id, title="A1", target_level=1, assessment_type="self"
        )
        create_assessment(
            db, org_id=org.id, title="A2", target_level=2, assessment_type="self"
        )

        items, total = list_assessments(db, org_id=org.id)
        assert total == 2
        assert len(items) == 2

    def test_filters_by_status(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a1 = create_assessment(
            db, org_id=org.id, title="A1", target_level=1, assessment_type="self"
        )
        create_assessment(
            db, org_id=org.id, title="A2", target_level=1, assessment_type="self"
        )
        start_assessment(db, a1.id)

        items, total = list_assessments(db, org_id=org.id, status="in_progress")
        assert total == 1
        assert items[0].status == "in_progress"

    def test_filters_by_level(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        create_assessment(
            db, org_id=org.id, title="L1", target_level=1, assessment_type="self"
        )
        create_assessment(
            db, org_id=org.id, title="L2", target_level=2, assessment_type="self"
        )

        items, total = list_assessments(db, org_id=org.id, target_level=2)
        assert total == 1
        assert items[0].target_level == 2

    def test_returns_empty_for_unknown_org(self, db: Session):
        items, total = list_assessments(db, org_id="unknown")
        assert total == 0
        assert items == []


# ---------------------------------------------------------------------------
# update_assessment
# ---------------------------------------------------------------------------


class TestUpdateAssessment:
    def test_updates_title(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Old", target_level=1, assessment_type="self"
        )

        updated = update_assessment(db, a.id, title="New Title")
        assert updated.title == "New Title"

    def test_updates_multiple_fields(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        user = _seed_user(db, org)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )

        updated = update_assessment(
            db, a.id, title="Updated", lead_assessor_id=user.id
        )
        assert updated.title == "Updated"
        assert updated.lead_assessor_id == user.id

    def test_raises_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            update_assessment(db, "nonexistent", title="X")

    def test_rejects_update_on_completed(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        start_assessment(db, a.id)
        submit_assessment(db, a.id)
        complete_assessment(db, a.id)

        with pytest.raises(ConflictError):
            update_assessment(db, a.id, title="Too Late")


# ---------------------------------------------------------------------------
# delete_assessment
# ---------------------------------------------------------------------------


class TestDeleteAssessment:
    def test_deletes_draft(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Draft", target_level=1, assessment_type="self"
        )
        aid = a.id

        delete_assessment(db, aid)

        with pytest.raises(NotFoundError):
            get_assessment(db, aid)

    def test_raises_conflict_for_non_draft(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        start_assessment(db, a.id)

        with pytest.raises(ConflictError):
            delete_assessment(db, a.id)

    def test_raises_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            delete_assessment(db, "nonexistent")


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    def test_start_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )

        result = start_assessment(db, a.id)
        assert result.status == "in_progress"
        assert result.started_at is not None

    def test_submit_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        start_assessment(db, a.id)

        result = submit_assessment(db, a.id)
        assert result.status == "under_review"

    def test_complete_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        start_assessment(db, a.id)
        submit_assessment(db, a.id)

        result = complete_assessment(db, a.id)
        assert result.status == "completed"
        assert result.completed_at is not None

    def test_cannot_start_non_draft(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        start_assessment(db, a.id)

        with pytest.raises(ConflictError):
            start_assessment(db, a.id)

    def test_cannot_submit_draft(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )

        with pytest.raises(ConflictError):
            submit_assessment(db, a.id)

    def test_cannot_complete_in_progress(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        a = create_assessment(
            db, org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        start_assessment(db, a.id)

        with pytest.raises(ConflictError):
            complete_assessment(db, a.id)
