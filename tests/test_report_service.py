"""Tests for report_service."""

import csv
import io

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.finding import Finding
from cmmc.models.organization import Organization
from cmmc.services.report_service import generate_assessment_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_org(db: Session) -> Organization:
    org = Organization(name="Acme Corp")
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


def _seed_full_assessment(db: Session) -> Assessment:
    """Create an org, domain, practices, assessment with evals, and findings."""
    org = _seed_org(db)
    _seed_domain(db, "AC", "Access Control")
    _seed_domain(db, "IA", "Identification & Authentication")
    _seed_practice(db, "AC.L1-3.1.1", "AC", level=1)
    _seed_practice(db, "AC.L1-3.1.2", "AC", level=1)
    _seed_practice(db, "IA.L1-3.5.1", "IA", level=1)

    a = Assessment(
        org_id=org.id,
        title="Q1 Self-Assessment",
        target_level=1,
        assessment_type="self",
        status="completed",
        overall_score=66.7,
        sprs_score=85,
    )
    db.add(a)
    db.flush()

    db.add(AssessmentPractice(assessment_id=a.id, practice_id="AC.L1-3.1.1", status="met"))
    db.add(AssessmentPractice(assessment_id=a.id, practice_id="AC.L1-3.1.2", status="not_met"))
    db.add(AssessmentPractice(assessment_id=a.id, practice_id="IA.L1-3.5.1", status="met"))

    db.add(Finding(
        assessment_id=a.id,
        practice_id="AC.L1-3.1.2",
        finding_type="minor_deficiency",
        severity="high",
        title="Missing access control policy",
        status="open",
    ))
    db.add(Finding(
        assessment_id=a.id,
        finding_type="observation",
        severity="low",
        title="Documentation gap",
        status="closed",
    ))

    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# CSV tests
# ---------------------------------------------------------------------------


class TestGenerateCSV:
    def test_returns_bytes(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="csv")
        assert isinstance(result, bytes)

    def test_csv_has_header_row(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="csv")
        reader = csv.reader(io.StringIO(result.decode("utf-8")))
        rows = list(reader)
        # Find the practice details header row
        header = next(r for r in rows if "Practice ID" in r)
        assert "Status" in header
        assert "Domain" in header

    def test_csv_has_practice_rows(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="csv")
        reader = csv.reader(io.StringIO(result.decode("utf-8")))
        rows = list(reader)
        # header + 3 practices
        assert len(rows) >= 4

    def test_csv_includes_practice_data(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="csv")
        text = result.decode("utf-8")
        assert "AC.L1-3.1.1" in text
        assert "met" in text
        assert "not_met" in text

    def test_csv_includes_findings_section(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="csv")
        text = result.decode("utf-8")
        assert "Findings" in text or "Finding" in text
        assert "Missing access control policy" in text

    def test_assessment_not_found_raises(self, db: Session):
        import pytest
        from cmmc.errors import NotFoundError

        with pytest.raises(NotFoundError):
            generate_assessment_report(db, "nonexistent", fmt="csv")


# ---------------------------------------------------------------------------
# PDF tests
# ---------------------------------------------------------------------------


class TestGeneratePDF:
    def test_returns_bytes(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="pdf")
        assert isinstance(result, bytes)

    def test_pdf_starts_with_magic_bytes(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="pdf")
        assert result[:5] == b"%PDF-"

    def test_pdf_has_nonzero_length(self, db: Session):
        a = _seed_full_assessment(db)
        result = generate_assessment_report(db, a.id, fmt="pdf")
        assert len(result) > 500

    def test_assessment_not_found_raises(self, db: Session):
        import pytest
        from cmmc.errors import NotFoundError

        with pytest.raises(NotFoundError):
            generate_assessment_report(db, "nonexistent", fmt="pdf")


# ---------------------------------------------------------------------------
# Invalid format
# ---------------------------------------------------------------------------


class TestInvalidFormat:
    def test_raises_on_unknown_format(self, db: Session):
        a = _seed_full_assessment(db)
        import pytest

        with pytest.raises(ValueError, match="Unsupported format"):
            generate_assessment_report(db, a.id, fmt="xlsx")
