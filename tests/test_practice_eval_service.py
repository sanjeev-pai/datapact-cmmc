"""Tests for practice evaluation service."""

import pytest
from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.organization import Organization
from cmmc.models.user import User
from cmmc.services.assessment_service import (
    create_assessment,
    start_assessment,
    submit_assessment,
)
from cmmc.services.practice_eval_service import (
    evaluate_practice,
    get_practice_evaluation,
    get_practice_evaluations,
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
    """Create two domains with practices at levels 1 and 2."""
    ac = CMMCDomain(domain_id="AC", name="Access Control")
    ia = CMMCDomain(domain_id="IA", name="Identification and Authentication")
    db.add_all([ac, ia])
    db.flush()

    practices = [
        CMMCPractice(practice_id="AC.L1-3.1.1", domain_ref="AC", level=1, title="Limit access"),
        CMMCPractice(practice_id="AC.L1-3.1.2", domain_ref="AC", level=1, title="Limit transactions"),
        CMMCPractice(practice_id="IA.L1-3.5.1", domain_ref="IA", level=1, title="Identify users"),
        CMMCPractice(practice_id="AC.L2-3.1.3", domain_ref="AC", level=2, title="Control CUI flow"),
    ]
    db.add_all(practices)
    db.flush()


def _create_in_progress_assessment(db: Session, org_id: str, level: int = 1):
    """Helper to create an assessment in in_progress status."""
    assessment = create_assessment(
        db, org_id=org_id, title="Test", target_level=level, assessment_type="self"
    )
    return start_assessment(db, assessment.id)


# ---------------------------------------------------------------------------
# evaluate_practice
# ---------------------------------------------------------------------------


class TestEvaluatePractice:
    def test_update_status(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        result = evaluate_practice(
            db, assessment.id, "AC.L1-3.1.1", status="met"
        )

        assert result.status == "met"
        assert result.practice_id == "AC.L1-3.1.1"

    def test_update_score(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        result = evaluate_practice(
            db, assessment.id, "AC.L1-3.1.1", score=0.75
        )

        assert result.score == 0.75

    def test_update_assessor_notes(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        result = evaluate_practice(
            db, assessment.id, "AC.L1-3.1.1", assessor_notes="Looks good"
        )

        assert result.assessor_notes == "Looks good"

    def test_update_multiple_fields(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        result = evaluate_practice(
            db,
            assessment.id,
            "AC.L1-3.1.1",
            status="not_met",
            score=0.0,
            assessor_notes="Missing controls",
        )

        assert result.status == "not_met"
        assert result.score == 0.0
        assert result.assessor_notes == "Missing controls"

    def test_rejects_when_draft(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = create_assessment(
            db, org_id=org.id, title="Draft", target_level=1, assessment_type="self"
        )

        with pytest.raises(ConflictError, match="in_progress"):
            evaluate_practice(db, assessment.id, "AC.L1-3.1.1", status="met")

    def test_rejects_when_under_review(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)
        submit_assessment(db, assessment.id)

        with pytest.raises(ConflictError, match="in_progress"):
            evaluate_practice(db, assessment.id, "AC.L1-3.1.1", status="met")

    def test_rejects_when_completed(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)
        submit_assessment(db, assessment.id)
        from cmmc.services.assessment_service import complete_assessment
        complete_assessment(db, assessment.id)

        with pytest.raises(ConflictError, match="in_progress"):
            evaluate_practice(db, assessment.id, "AC.L1-3.1.1", status="met")

    def test_assessment_not_found(self, db: Session):
        with pytest.raises(NotFoundError, match="Assessment"):
            evaluate_practice(db, "nonexistent", "AC.L1-3.1.1", status="met")

    def test_practice_not_found(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        with pytest.raises(NotFoundError, match="Practice"):
            evaluate_practice(db, assessment.id, "NONEXIST", status="met")

    def test_successive_updates(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        evaluate_practice(db, assessment.id, "AC.L1-3.1.1", status="not_met")
        result = evaluate_practice(
            db, assessment.id, "AC.L1-3.1.1", status="met", score=1.0
        )

        assert result.status == "met"
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# get_practice_evaluations
# ---------------------------------------------------------------------------


class TestGetPracticeEvaluations:
    def test_returns_all_for_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        results = get_practice_evaluations(db, assessment.id)

        # Level 1 assessment should have 3 practices (AC.L1-3.1.1, AC.L1-3.1.2, IA.L1-3.5.1)
        assert len(results) == 3

    def test_filter_by_status(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        evaluate_practice(db, assessment.id, "AC.L1-3.1.1", status="met")

        met = get_practice_evaluations(db, assessment.id, status="met")
        assert len(met) == 1
        assert met[0].practice_id == "AC.L1-3.1.1"

        not_eval = get_practice_evaluations(db, assessment.id, status="not_evaluated")
        assert len(not_eval) == 2

    def test_filter_by_domain(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        ac_practices = get_practice_evaluations(db, assessment.id, domain="AC")
        assert len(ac_practices) == 2
        for p in ac_practices:
            assert p.practice_id.startswith("AC.")

        ia_practices = get_practice_evaluations(db, assessment.id, domain="IA")
        assert len(ia_practices) == 1
        assert ia_practices[0].practice_id.startswith("IA.")

    def test_filter_by_status_and_domain(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        evaluate_practice(db, assessment.id, "AC.L1-3.1.1", status="met")

        results = get_practice_evaluations(db, assessment.id, status="met", domain="AC")
        assert len(results) == 1
        assert results[0].practice_id == "AC.L1-3.1.1"

        results = get_practice_evaluations(db, assessment.id, status="met", domain="IA")
        assert len(results) == 0

    def test_assessment_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            get_practice_evaluations(db, "nonexistent")

    def test_empty_when_no_practices(self, db: Session):
        org = _seed_org(db)
        # No practices seeded — assessment will have 0 practices
        assessment = create_assessment(
            db, org_id=org.id, title="Empty", target_level=1, assessment_type="self"
        )

        results = get_practice_evaluations(db, assessment.id)
        assert results == []

    def test_level2_includes_level1_practices(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id, level=2)

        results = get_practice_evaluations(db, assessment.id)
        # L2 should include L1 (3) + L2 (1) = 4 practices
        assert len(results) == 4


# ---------------------------------------------------------------------------
# get_practice_evaluation
# ---------------------------------------------------------------------------


class TestGetPracticeEvaluation:
    def test_returns_single(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        result = get_practice_evaluation(db, assessment.id, "AC.L1-3.1.1")

        assert result.practice_id == "AC.L1-3.1.1"
        assert result.assessment_id == assessment.id
        assert result.status == "not_evaluated"

    def test_returns_evaluated_practice(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        evaluate_practice(
            db, assessment.id, "AC.L1-3.1.1",
            status="met", score=1.0, assessor_notes="All good"
        )

        result = get_practice_evaluation(db, assessment.id, "AC.L1-3.1.1")
        assert result.status == "met"
        assert result.score == 1.0
        assert result.assessor_notes == "All good"

    def test_assessment_not_found(self, db: Session):
        with pytest.raises(NotFoundError, match="Assessment"):
            get_practice_evaluation(db, "nonexistent", "AC.L1-3.1.1")

    def test_practice_not_found(self, db: Session):
        org = _seed_org(db)
        _seed_practices(db)
        assessment = _create_in_progress_assessment(db, org.id)

        with pytest.raises(NotFoundError, match="Practice"):
            get_practice_evaluation(db, assessment.id, "NONEXIST")
