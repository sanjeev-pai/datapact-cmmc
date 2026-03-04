"""Tests for demo assessment seed data (practice evaluations, findings, POAMs)."""

from cmmc.models.assessment import AssessmentPractice, Assessment
from cmmc.models.finding import Finding
from cmmc.models.poam import POAM, POAMItem
from cmmc.services.seed_service import seed_all


class TestDemoSeed:
    """Tests for demo seed data loaded from demo_assessment.yaml."""

    def test_seed_creates_practice_evaluations(self, db):
        counts = seed_all(db, seed_demo=True)
        assert counts["practice_evaluations"] > 0
        # Acme L1 has 14 evaluations in YAML, Pinnacle L2 has 17+18 = 35
        # Total: 14 + 35 = 49 evaluations
        evaluated = (
            db.query(AssessmentPractice)
            .filter(AssessmentPractice.status != "not_evaluated")
            .count()
        )
        assert evaluated == counts["practice_evaluations"]

    def test_acme_l1_evaluations(self, db):
        seed_all(db, seed_demo=True)
        assessment = db.query(Assessment).filter_by(
            title="Acme L1 Self-Assessment (FY25)"
        ).first()
        assert assessment is not None

        met = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id, status="met")
            .count()
        )
        not_met = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id, status="not_met")
            .count()
        )
        partially = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id, status="partially_met")
            .count()
        )
        not_evaluated = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id, status="not_evaluated")
            .count()
        )
        # Acme L1 has 17 practices total, 14 evaluated in YAML
        assert met == 9
        assert not_met == 2
        assert partially == 3
        assert not_evaluated == 3  # MP.L1-3.8.3, SC.L1-3.13.5, SI.L1-3.14.5

    def test_pinnacle_l2_all_l1_met(self, db):
        seed_all(db, seed_demo=True)
        assessment = db.query(Assessment).filter_by(
            title="Pinnacle L2 Self-Assessment (FY25)"
        ).first()
        assert assessment is not None

        # All 17 L1 practices should be met
        l1_met = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id, status="met")
            .filter(AssessmentPractice.practice_id.like("%.L1-%"))
            .count()
        )
        assert l1_met == 17

    def test_seed_creates_findings(self, db):
        counts = seed_all(db, seed_demo=True)
        assert counts["findings"] > 0
        total_findings = db.query(Finding).count()
        assert total_findings == counts["findings"]

    def test_acme_findings(self, db):
        seed_all(db, seed_demo=True)
        assessment = db.query(Assessment).filter_by(
            title="Acme L1 Self-Assessment (FY25)"
        ).first()
        findings = db.query(Finding).filter_by(assessment_id=assessment.id).all()
        assert len(findings) == 4
        # Check severity distribution
        severities = {f.severity for f in findings}
        assert "high" in severities
        assert "medium" in severities
        assert "low" in severities

    def test_pinnacle_findings(self, db):
        seed_all(db, seed_demo=True)
        assessment = db.query(Assessment).filter_by(
            title="Pinnacle L2 Self-Assessment (FY25)"
        ).first()
        findings = db.query(Finding).filter_by(assessment_id=assessment.id).all()
        assert len(findings) == 4
        statuses = {f.status for f in findings}
        assert "open" in statuses
        assert "remediated" in statuses

    def test_seed_creates_poams(self, db):
        counts = seed_all(db, seed_demo=True)
        assert counts["poams"] == 2
        assert db.query(POAM).count() == 2

    def test_poam_items_created(self, db):
        seed_all(db, seed_demo=True)
        # 4 items per POAM = 8 total
        assert db.query(POAMItem).count() == 8

    def test_poam_items_linked_to_findings(self, db):
        seed_all(db, seed_demo=True)
        # All POAM items should be linked to findings
        linked = db.query(POAMItem).filter(POAMItem.finding_id.isnot(None)).count()
        assert linked == 8

    def test_poam_item_statuses(self, db):
        seed_all(db, seed_demo=True)
        statuses = {
            row[0] for row in db.query(POAMItem.status).distinct().all()
        }
        assert statuses == {"open", "in_progress", "completed"}

    def test_poam_overdue_items(self, db):
        seed_all(db, seed_demo=True)
        from datetime import date

        overdue = (
            db.query(POAMItem)
            .filter(
                POAMItem.scheduled_completion < date(2026, 3, 3),
                POAMItem.status != "completed",
            )
            .count()
        )
        # PE.L1-3.10.4 milestone scheduled for 2026-03-01, status open → overdue
        assert overdue >= 1

    def test_demo_seed_idempotent(self, db):
        seed_all(db, seed_demo=True)
        seed_all(db, seed_demo=True)
        # Counts should not double
        assert db.query(Finding).count() == 8
        assert db.query(POAM).count() == 2
        assert db.query(POAMItem).count() == 8

    def test_seed_without_demo(self, db):
        counts = seed_all(db, seed_demo=False)
        assert "practice_evaluations" not in counts
        assert "findings" not in counts
        assert "poams" not in counts
        # No findings or POAMs created
        assert db.query(Finding).count() == 0
        assert db.query(POAM).count() == 0
        # All assessment practices remain not_evaluated
        not_evaluated = (
            db.query(AssessmentPractice)
            .filter_by(status="not_evaluated")
            .count()
        )
        total = db.query(AssessmentPractice).count()
        assert not_evaluated == total
