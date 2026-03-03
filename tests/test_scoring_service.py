"""Tests for SPRS scoring service."""

import pytest
from sqlalchemy.orm import Session

from cmmc.errors import NotFoundError
from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.organization import Organization
from cmmc.services.scoring_service import (
    calculate_overall_score,
    calculate_sprs_score,
    get_nist_ref,
    SPRS_WEIGHTS,
)


def _seed_org(db: Session) -> Organization:
    org = Organization(name="Test Org")
    db.add(org)
    db.flush()
    return org


def _seed_domain(db: Session, domain_id: str = "AC", name: str = "Access Control"):
    d = db.query(CMMCDomain).filter_by(domain_id=domain_id).first()
    if not d:
        d = CMMCDomain(domain_id=domain_id, name=name)
        db.add(d)
        db.flush()
    return d


def _seed_practice(db: Session, practice_id: str, domain_ref: str, level: int):
    p = db.query(CMMCPractice).filter_by(practice_id=practice_id).first()
    if not p:
        p = CMMCPractice(
            practice_id=practice_id, domain_ref=domain_ref,
            level=level, title=f"Practice {practice_id}",
        )
        db.add(p)
        db.flush()
    return p


def _create_assessment_with_practices(
    db: Session,
    org_id: str,
    practice_configs: list[tuple[str, str]],  # (practice_id, status)
    target_level: int = 2,
) -> Assessment:
    """Create assessment with specific practice statuses."""
    assessment = Assessment(
        org_id=org_id, title="Test", target_level=target_level,
        assessment_type="self", status="in_progress",
    )
    db.add(assessment)
    db.flush()

    for pid, status in practice_configs:
        db.add(AssessmentPractice(
            assessment_id=assessment.id, practice_id=pid, status=status,
        ))

    db.commit()
    db.refresh(assessment)
    return assessment


# ---------------------------------------------------------------------------
# get_nist_ref
# ---------------------------------------------------------------------------

class TestGetNistRef:
    def test_l1_practice(self):
        assert get_nist_ref("AC.L1-3.1.1") == "3.1.1"

    def test_l2_practice(self):
        assert get_nist_ref("SC.L2-3.13.11") == "3.13.11"

    def test_l3_practice(self):
        assert get_nist_ref("AC.L3-3.1.2e") == "3.1.2e"

    def test_unknown_format(self):
        assert get_nist_ref("UNKNOWN") is None


# ---------------------------------------------------------------------------
# SPRS_WEIGHTS validation
# ---------------------------------------------------------------------------

class TestSPRSWeights:
    def test_total_weight_is_313(self):
        """Sum of all weights should be 313 (110 - (-203) = 313)."""
        total = sum(SPRS_WEIGHTS.values())
        assert total == 313

    def test_weight_count(self):
        """Should have 109 scored requirements (110 minus 3.12.4 which is N/A)."""
        assert len(SPRS_WEIGHTS) == 109

    def test_all_weights_valid(self):
        """All weights should be 1, 3, or 5."""
        for req, weight in SPRS_WEIGHTS.items():
            assert weight in (1, 3, 5), f"{req} has invalid weight {weight}"

    def test_known_5_point_requirements(self):
        assert SPRS_WEIGHTS["3.1.1"] == 5
        assert SPRS_WEIGHTS["3.5.3"] == 5
        assert SPRS_WEIGHTS["3.13.11"] == 5
        assert SPRS_WEIGHTS["3.14.6"] == 5

    def test_known_3_point_requirements(self):
        assert SPRS_WEIGHTS["3.1.5"] == 3
        assert SPRS_WEIGHTS["3.8.1"] == 3
        assert SPRS_WEIGHTS["3.9.1"] == 3

    def test_known_1_point_requirements(self):
        assert SPRS_WEIGHTS["3.1.3"] == 1
        assert SPRS_WEIGHTS["3.5.4"] == 1
        assert SPRS_WEIGHTS["3.13.3"] == 1

    def test_3_12_4_excluded(self):
        """3.12.4 (SSP) should not be in weights — it's N/A for scoring."""
        assert "3.12.4" not in SPRS_WEIGHTS


# ---------------------------------------------------------------------------
# calculate_sprs_score
# ---------------------------------------------------------------------------

class TestCalculateSPRSScore:
    def test_all_met_returns_110(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_domain(db, "IA")

        # Seed 3 practices that have SPRS weights
        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)   # weight 5
        _seed_practice(db, "AC.L2-3.1.3", "AC", 2)   # weight 1
        _seed_practice(db, "IA.L1-3.5.1", "IA", 1)   # weight 5

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "met"),
            ("AC.L2-3.1.3", "met"),
            ("IA.L1-3.5.1", "met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        # All met → 110 (no deductions)
        assert score == 110

    def test_deducts_for_not_met(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")

        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)   # weight 5
        _seed_practice(db, "AC.L2-3.1.3", "AC", 2)   # weight 1

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "not_met"),
            ("AC.L2-3.1.3", "met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110 - 5  # 105

    def test_deducts_for_not_evaluated(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")

        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)   # weight 5
        _seed_practice(db, "AC.L2-3.1.3", "AC", 2)   # weight 1

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "not_evaluated"),
            ("AC.L2-3.1.3", "met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110 - 5  # 105

    def test_deducts_for_partially_met(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")

        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)   # weight 5

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "partially_met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110 - 5  # partially_met still deducts full weight

    def test_not_applicable_no_deduction(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")

        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)   # weight 5
        _seed_practice(db, "AC.L2-3.1.3", "AC", 2)   # weight 1

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "not_applicable"),
            ("AC.L2-3.1.3", "met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110  # N/A = no deduction

    def test_multiple_deductions(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_domain(db, "IA")

        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)   # weight 5
        _seed_practice(db, "AC.L2-3.1.5", "AC", 2)   # weight 3
        _seed_practice(db, "IA.L1-3.5.1", "IA", 1)   # weight 5

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "not_met"),
            ("AC.L2-3.1.5", "not_met"),
            ("IA.L1-3.5.1", "met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110 - 5 - 3  # 102

    def test_practice_without_weight_defaults_to_1(self, db: Session):
        """Practices not in weight table (e.g. L3 or custom) default to weight 1."""
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_practice(db, "AC.L3-3.1.2e", "AC", 3)  # L3, not in weight table

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L3-3.1.2e", "not_met"),
        ])

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110 - 1  # default weight 1

    def test_assessment_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            calculate_sprs_score(db, "nonexistent")

    def test_empty_assessment(self, db: Session):
        org = _seed_org(db)
        assessment = Assessment(
            org_id=org.id, title="Empty", target_level=1,
            assessment_type="self", status="in_progress",
        )
        db.add(assessment)
        db.commit()

        score = calculate_sprs_score(db, assessment.id)
        assert score == 110  # no practices = no deductions


# ---------------------------------------------------------------------------
# calculate_overall_score
# ---------------------------------------------------------------------------

class TestCalculateOverallScore:
    def test_all_met(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)
        _seed_practice(db, "AC.L1-3.1.2", "AC", 1)

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "met"),
            ("AC.L1-3.1.2", "met"),
        ])

        pct = calculate_overall_score(db, assessment.id)
        assert pct == 100.0

    def test_half_met(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)
        _seed_practice(db, "AC.L1-3.1.2", "AC", 1)

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "met"),
            ("AC.L1-3.1.2", "not_met"),
        ])

        pct = calculate_overall_score(db, assessment.id)
        assert pct == 50.0

    def test_none_met(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "not_met"),
        ])

        pct = calculate_overall_score(db, assessment.id)
        assert pct == 0.0

    def test_excludes_not_applicable(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)
        _seed_practice(db, "AC.L1-3.1.2", "AC", 1)

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "met"),
            ("AC.L1-3.1.2", "not_applicable"),
        ])

        pct = calculate_overall_score(db, assessment.id)
        # 1 met out of 1 scorable = 100%
        assert pct == 100.0

    def test_empty_returns_zero(self, db: Session):
        org = _seed_org(db)
        assessment = Assessment(
            org_id=org.id, title="Empty", target_level=1,
            assessment_type="self", status="in_progress",
        )
        db.add(assessment)
        db.commit()

        pct = calculate_overall_score(db, assessment.id)
        assert pct == 0.0

    def test_all_not_applicable_returns_zero(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC")
        _seed_practice(db, "AC.L1-3.1.1", "AC", 1)

        assessment = _create_assessment_with_practices(db, org.id, [
            ("AC.L1-3.1.1", "not_applicable"),
        ])

        pct = calculate_overall_score(db, assessment.id)
        assert pct == 0.0  # no scorable practices

    def test_assessment_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            calculate_overall_score(db, "nonexistent")
