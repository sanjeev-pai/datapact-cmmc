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
        # YAML provides 453 evaluations + fill adds ~241 = 694 total evaluated
        evaluated = (
            db.query(AssessmentPractice)
            .filter(AssessmentPractice.status != "not_evaluated")
            .count()
        )
        assert evaluated == counts["practice_evaluations"] + counts["filled_evaluations"]

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
        # Acme L1 has 17 practices total, all 17 evaluated in YAML
        assert met == 10
        assert not_met == 3
        assert partially == 4
        assert not_evaluated == 0

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
        assert len(findings) == 5
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
        # Mrisan (2) + Acme (3) + Pinnacle (2) + Mrisan L3 (1) = 8 POAMs
        assert counts["poams"] == 8
        assert db.query(POAM).count() == 8

    def test_poam_items_created(self, db):
        seed_all(db, seed_demo=True)
        # All POAMs: 2+2+4+4+4+4+4+2 = 26 items
        assert db.query(POAMItem).count() == 26

    def test_poam_items_linked_to_findings(self, db):
        seed_all(db, seed_demo=True)
        # All POAM items should be linked to findings
        linked = db.query(POAMItem).filter(POAMItem.finding_id.isnot(None)).count()
        assert linked == 26

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
        assert db.query(Finding).count() == 29
        assert db.query(POAM).count() == 8
        assert db.query(POAMItem).count() == 26

    def test_mrisan_l1_scores_calculated(self, db):
        seed_all(db, seed_demo=True)
        assessment = db.query(Assessment).filter_by(
            title="Mrisan L1 Self-Assessment (FY25)"
        ).first()
        assert assessment is not None
        assert assessment.status == "completed"
        # Scores should be non-null after seed
        assert assessment.sprs_score is not None
        assert assessment.overall_score is not None
        assert assessment.overall_score > 0

    def test_mrisan_findings(self, db):
        seed_all(db, seed_demo=True)
        assessment = db.query(Assessment).filter_by(
            title="Mrisan L1 Self-Assessment (FY25)"
        ).first()
        findings = db.query(Finding).filter_by(assessment_id=assessment.id).all()
        assert len(findings) == 2

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
