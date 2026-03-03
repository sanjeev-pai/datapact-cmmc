"""Tests for dashboard_service."""

import pytest
from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.finding import Finding
from cmmc.models.organization import Organization
from cmmc.services.dashboard_service import (
    get_assessment_timeline,
    get_compliance_summary,
    get_domain_compliance,
    get_findings_summary,
    get_sprs_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_org(db: Session, name: str = "Acme Corp") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.flush()
    return org


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
    finding_type: str = "observation",
) -> Finding:
    f = Finding(
        assessment_id=assessment_id,
        finding_type=finding_type,
        severity=severity,
        title=f"{severity} finding",
        status=status,
    )
    db.add(f)
    db.flush()
    return f


# ---------------------------------------------------------------------------
# get_compliance_summary
# ---------------------------------------------------------------------------


class TestGetComplianceSummary:
    def test_returns_none_for_levels_without_completed_assessment(self, db: Session):
        org = _seed_org(db)
        result = get_compliance_summary(db, org.id)
        assert result["level_1"] is None
        assert result["level_2"] is None
        assert result["level_3"] is None

    def test_calculates_percentage_for_completed_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC", level=1)
        _seed_practice(db, "AC.L1-3.1.2", "AC", level=1)

        a = _seed_assessment(db, org.id, target_level=1, status="completed")
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        _seed_eval(db, a.id, "AC.L1-3.1.2", "not_met")
        db.commit()

        result = get_compliance_summary(db, org.id)
        assert result["level_1"] == 50.0
        assert result["level_2"] is None

    def test_excludes_not_applicable_from_total(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC", level=1)
        _seed_practice(db, "AC.L1-3.1.2", "AC", level=1)

        a = _seed_assessment(db, org.id, target_level=1, status="completed")
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        _seed_eval(db, a.id, "AC.L1-3.1.2", "not_applicable")
        db.commit()

        result = get_compliance_summary(db, org.id)
        assert result["level_1"] == 100.0

    def test_uses_most_recent_completed_assessment(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC", level=1)

        # Older assessment — 0%
        a1 = _seed_assessment(db, org.id, title="Old", target_level=1, status="completed")
        _seed_eval(db, a1.id, "AC.L1-3.1.1", "not_met")

        # Newer assessment — 100%
        a2 = _seed_assessment(db, org.id, title="New", target_level=1, status="completed")
        _seed_eval(db, a2.id, "AC.L1-3.1.1", "met")
        db.commit()

        result = get_compliance_summary(db, org.id)
        assert result["level_1"] == 100.0

    def test_ignores_draft_assessments(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC", level=1)

        a = _seed_assessment(db, org.id, target_level=1, status="draft")
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        db.commit()

        result = get_compliance_summary(db, org.id)
        assert result["level_1"] is None


# ---------------------------------------------------------------------------
# get_domain_compliance
# ---------------------------------------------------------------------------


class TestGetDomainCompliance:
    def test_returns_per_domain_scores(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC", "Access Control")
        _seed_domain(db, "IA", "Identification & Authentication")
        _seed_practice(db, "AC.L1-3.1.1", "AC")
        _seed_practice(db, "AC.L1-3.1.2", "AC")
        _seed_practice(db, "IA.L1-3.5.1", "IA")

        a = _seed_assessment(db, org.id, target_level=1)
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        _seed_eval(db, a.id, "AC.L1-3.1.2", "not_met")
        _seed_eval(db, a.id, "IA.L1-3.5.1", "met")
        db.commit()

        result = get_domain_compliance(db, a.id)
        ac = next(d for d in result if d["domain_id"] == "AC")
        ia = next(d for d in result if d["domain_id"] == "IA")

        assert ac["met"] == 1
        assert ac["total"] == 2
        assert ac["percentage"] == 50.0
        assert ia["met"] == 1
        assert ia["total"] == 1
        assert ia["percentage"] == 100.0

    def test_excludes_not_applicable(self, db: Session):
        org = _seed_org(db)
        _seed_domain(db, "AC", "Access Control")
        _seed_practice(db, "AC.L1-3.1.1", "AC")
        _seed_practice(db, "AC.L1-3.1.2", "AC")

        a = _seed_assessment(db, org.id, target_level=1)
        _seed_eval(db, a.id, "AC.L1-3.1.1", "met")
        _seed_eval(db, a.id, "AC.L1-3.1.2", "not_applicable")
        db.commit()

        result = get_domain_compliance(db, a.id)
        ac = next(d for d in result if d["domain_id"] == "AC")
        assert ac["total"] == 1
        assert ac["percentage"] == 100.0

    def test_returns_empty_for_no_practices(self, db: Session):
        org = _seed_org(db)
        a = _seed_assessment(db, org.id)
        db.commit()
        result = get_domain_compliance(db, a.id)
        assert result == []

    def test_assessment_not_found(self, db: Session):
        result = get_domain_compliance(db, "nonexistent")
        assert result == []


# ---------------------------------------------------------------------------
# get_sprs_summary
# ---------------------------------------------------------------------------


class TestGetSprsSummary:
    def test_returns_current_and_history(self, db: Session):
        org = _seed_org(db)
        _seed_assessment(db, org.id, title="A1", sprs_score=72, status="completed")
        _seed_assessment(db, org.id, title="A2", sprs_score=95, status="completed")
        db.commit()

        result = get_sprs_summary(db, org.id)
        assert result["current"] == 95
        assert len(result["history"]) == 2
        assert result["history"][0]["title"] == "A2"  # newest first
        assert result["history"][1]["title"] == "A1"

    def test_returns_none_when_no_scores(self, db: Session):
        org = _seed_org(db)
        result = get_sprs_summary(db, org.id)
        assert result["current"] is None
        assert result["history"] == []

    def test_excludes_assessments_without_sprs(self, db: Session):
        org = _seed_org(db)
        _seed_assessment(db, org.id, title="No Score", sprs_score=None)
        _seed_assessment(db, org.id, title="Has Score", sprs_score=80)
        db.commit()

        result = get_sprs_summary(db, org.id)
        assert result["current"] == 80
        assert len(result["history"]) == 1


# ---------------------------------------------------------------------------
# get_assessment_timeline
# ---------------------------------------------------------------------------


class TestGetAssessmentTimeline:
    def test_returns_recent_assessments(self, db: Session):
        org = _seed_org(db)
        _seed_assessment(db, org.id, title="A1", status="completed")
        _seed_assessment(db, org.id, title="A2", status="in_progress")
        db.commit()

        result = get_assessment_timeline(db, org.id)
        assert len(result) == 2
        assert result[0]["title"] == "A2"  # newest first

    def test_respects_limit(self, db: Session):
        org = _seed_org(db)
        for i in range(5):
            _seed_assessment(db, org.id, title=f"A{i}")
        db.commit()

        result = get_assessment_timeline(db, org.id, limit=3)
        assert len(result) == 3

    def test_returns_empty_for_no_assessments(self, db: Session):
        org = _seed_org(db)
        result = get_assessment_timeline(db, org.id)
        assert result == []

    def test_includes_assessment_fields(self, db: Session):
        org = _seed_org(db)
        _seed_assessment(
            db, org.id, title="Full",
            target_level=2, status="completed",
            overall_score=85.5, sprs_score=95,
        )
        db.commit()

        result = get_assessment_timeline(db, org.id)
        item = result[0]
        assert item["title"] == "Full"
        assert item["target_level"] == 2
        assert item["status"] == "completed"
        assert item["overall_score"] == 85.5
        assert item["sprs_score"] == 95


# ---------------------------------------------------------------------------
# get_findings_summary
# ---------------------------------------------------------------------------


class TestGetFindingsSummary:
    def test_counts_by_severity_and_status(self, db: Session):
        org = _seed_org(db)
        a = _seed_assessment(db, org.id)
        _seed_finding(db, a.id, severity="critical", status="open")
        _seed_finding(db, a.id, severity="critical", status="open")
        _seed_finding(db, a.id, severity="high", status="closed")
        _seed_finding(db, a.id, severity="low", status="open")
        db.commit()

        result = get_findings_summary(db, a.id)
        assert result["total"] == 4
        assert result["by_severity"]["critical"] == 2
        assert result["by_severity"]["high"] == 1
        assert result["by_severity"]["low"] == 1
        assert result["by_status"]["open"] == 3
        assert result["by_status"]["closed"] == 1

    def test_returns_zeros_for_no_findings(self, db: Session):
        org = _seed_org(db)
        a = _seed_assessment(db, org.id)
        db.commit()

        result = get_findings_summary(db, a.id)
        assert result["total"] == 0
        assert result["by_severity"] == {}
        assert result["by_status"] == {}

    def test_nonexistent_assessment_returns_empty(self, db: Session):
        result = get_findings_summary(db, "nonexistent")
        assert result["total"] == 0
