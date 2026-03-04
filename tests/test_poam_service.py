"""Tests for POA&M service."""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.assessment import Assessment
from cmmc.models.finding import Finding
from cmmc.models.organization import Organization
from cmmc.models.poam import POAM, POAMItem
from cmmc.services.poam_service import (
    activate_poam,
    add_item,
    complete_poam,
    create_poam,
    delete_poam,
    generate_from_assessment,
    get_item,
    get_overdue_items,
    get_poam,
    list_poams,
    remove_item,
    update_item,
    update_poam,
)


def _seed_org(db: Session) -> Organization:
    org = Organization(name="Test Org")
    db.add(org)
    db.flush()
    return org


def _seed_assessment(db: Session, org: Organization) -> Assessment:
    a = Assessment(
        org_id=org.id,
        title="L2 Assessment",
        target_level=2,
        assessment_type="self",
        status="completed",
    )
    db.add(a)
    db.flush()
    return a


def _seed_findings(db: Session, assessment: Assessment, count: int = 3) -> list[Finding]:
    findings = []
    for i in range(count):
        f = Finding(
            assessment_id=assessment.id,
            practice_id=f"AC.L2-3.1.{i + 1}",
            finding_type="deficiency",
            severity="high",
            title=f"Finding {i + 1}",
            description=f"Description {i + 1}",
            status="open",
        )
        db.add(f)
        findings.append(f)
    db.flush()
    return findings


# ---------------------------------------------------------------------------
# create_poam
# ---------------------------------------------------------------------------


class TestCreatePOAM:
    def test_creates_draft_poam(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Remediation Plan")

        assert poam.id is not None
        assert poam.org_id == org.id
        assert poam.title == "Remediation Plan"
        assert poam.status == "draft"
        assert poam.assessment_id is None

    def test_creates_with_assessment(self, db: Session):
        org = _seed_org(db)
        assessment = _seed_assessment(db, org)
        poam = create_poam(
            db, org_id=org.id, title="Post-Assessment", assessment_id=assessment.id
        )
        assert poam.assessment_id == assessment.id


# ---------------------------------------------------------------------------
# get_poam
# ---------------------------------------------------------------------------


class TestGetPOAM:
    def test_returns_poam(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Test")
        fetched = get_poam(db, poam.id)
        assert fetched.id == poam.id

    def test_raises_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            get_poam(db, "nonexistent")


# ---------------------------------------------------------------------------
# list_poams
# ---------------------------------------------------------------------------


class TestListPOAMs:
    def test_lists_all(self, db: Session):
        org = _seed_org(db)
        create_poam(db, org_id=org.id, title="Plan A")
        create_poam(db, org_id=org.id, title="Plan B")

        items, total = list_poams(db)
        assert total == 2

    def test_filters_by_org(self, db: Session):
        org1 = _seed_org(db)
        org2 = Organization(name="Other Org")
        db.add(org2)
        db.flush()

        create_poam(db, org_id=org1.id, title="Org1 Plan")
        create_poam(db, org_id=org2.id, title="Org2 Plan")

        items, total = list_poams(db, org_id=org1.id)
        assert total == 1
        assert items[0].title == "Org1 Plan"

    def test_filters_by_status(self, db: Session):
        org = _seed_org(db)
        create_poam(db, org_id=org.id, title="Draft")
        p2 = create_poam(db, org_id=org.id, title="Active")
        activate_poam(db, p2.id)

        items, total = list_poams(db, status="active")
        assert total == 1
        assert items[0].title == "Active"

    def test_filters_by_assessment(self, db: Session):
        org = _seed_org(db)
        assessment = _seed_assessment(db, org)
        create_poam(db, org_id=org.id, title="With Assessment", assessment_id=assessment.id)
        create_poam(db, org_id=org.id, title="Without Assessment")

        items, total = list_poams(db, assessment_id=assessment.id)
        assert total == 1
        assert items[0].title == "With Assessment"


# ---------------------------------------------------------------------------
# update_poam
# ---------------------------------------------------------------------------


class TestUpdatePOAM:
    def test_updates_title(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Original")
        updated = update_poam(db, poam.id, title="Updated")
        assert updated.title == "Updated"

    def test_rejects_update_on_completed(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Test")
        activate_poam(db, poam.id)
        complete_poam(db, poam.id)

        with pytest.raises(ConflictError):
            update_poam(db, poam.id, title="Nope")


# ---------------------------------------------------------------------------
# delete_poam
# ---------------------------------------------------------------------------


class TestDeletePOAM:
    def test_deletes_draft(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Draft Plan")
        add_item(db, poam.id, milestone="Item 1")

        delete_poam(db, poam.id)

        assert db.query(POAM).filter_by(id=poam.id).first() is None
        assert db.query(POAMItem).filter_by(poam_id=poam.id).count() == 0

    def test_rejects_delete_non_draft(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Active Plan")
        activate_poam(db, poam.id)

        with pytest.raises(ConflictError):
            delete_poam(db, poam.id)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestPOAMTransitions:
    def test_draft_to_active(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        activated = activate_poam(db, poam.id)
        assert activated.status == "active"

    def test_active_to_completed(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        activate_poam(db, poam.id)
        completed = complete_poam(db, poam.id)
        assert completed.status == "completed"

    def test_rejects_draft_to_completed(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        with pytest.raises(ConflictError):
            complete_poam(db, poam.id)

    def test_rejects_active_to_draft(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        activate_poam(db, poam.id)
        with pytest.raises(ConflictError):
            _transition_from_service(db, poam.id, "draft")

    def test_completed_cannot_transition(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        activate_poam(db, poam.id)
        complete_poam(db, poam.id)
        with pytest.raises(ConflictError):
            activate_poam(db, poam.id)


def _transition_from_service(db: Session, poam_id: str, target: str):
    """Helper to invoke private transition."""
    from cmmc.services.poam_service import _transition_poam
    return _transition_poam(db, poam_id, target)


# ---------------------------------------------------------------------------
# Item CRUD
# ---------------------------------------------------------------------------


class TestAddItem:
    def test_creates_item(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(
            db,
            poam.id,
            milestone="Deploy MFA",
            practice_id="AC.L2-3.1.5",
            scheduled_completion=date(2026, 6, 30),
        )

        assert item.id is not None
        assert item.poam_id == poam.id
        assert item.milestone == "Deploy MFA"
        assert item.status == "open"
        assert item.risk_accepted is False

    def test_rejects_add_to_completed(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        activate_poam(db, poam.id)
        complete_poam(db, poam.id)

        with pytest.raises(ConflictError):
            add_item(db, poam.id, milestone="Nope")


class TestGetItem:
    def test_returns_item(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Test")
        fetched = get_item(db, item.id)
        assert fetched.id == item.id

    def test_raises_not_found(self, db: Session):
        with pytest.raises(NotFoundError):
            get_item(db, "nonexistent")


class TestUpdateItem:
    def test_updates_fields(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Original")

        updated = update_item(
            db,
            item.id,
            milestone="Updated Milestone",
            scheduled_completion=date(2026, 9, 30),
            risk_accepted=True,
        )
        assert updated.milestone == "Updated Milestone"
        assert updated.scheduled_completion == date(2026, 9, 30)
        assert updated.risk_accepted is True

    def test_transitions_item_status(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Work")

        updated = update_item(db, item.id, status="in_progress")
        assert updated.status == "in_progress"

        completed = update_item(db, item.id, status="completed")
        assert completed.status == "completed"

    def test_rejects_invalid_transition(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Work")

        with pytest.raises(ConflictError):
            update_item(db, item.id, status="completed")  # open -> completed invalid

    def test_rejects_update_on_completed_poam(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Work")
        activate_poam(db, poam.id)
        complete_poam(db, poam.id)

        with pytest.raises(ConflictError):
            update_item(db, item.id, milestone="Nope")


class TestRemoveItem:
    def test_removes_item(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Removable")

        remove_item(db, item.id)
        assert db.query(POAMItem).filter_by(id=item.id).first() is None

    def test_rejects_remove_from_completed(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")
        item = add_item(db, poam.id, milestone="Locked")
        activate_poam(db, poam.id)
        complete_poam(db, poam.id)

        with pytest.raises(ConflictError):
            remove_item(db, item.id)


# ---------------------------------------------------------------------------
# Auto-generation from findings
# ---------------------------------------------------------------------------


class TestGenerateFromAssessment:
    def test_generates_items_from_open_findings(self, db: Session):
        org = _seed_org(db)
        assessment = _seed_assessment(db, org)
        findings = _seed_findings(db, assessment, count=3)
        poam = create_poam(db, org_id=org.id, title="Auto-gen", assessment_id=assessment.id)

        items = generate_from_assessment(db, poam.id, assessment.id)

        assert len(items) == 3
        finding_ids = {f.id for f in findings}
        for item in items:
            assert item.finding_id in finding_ids
            assert item.status == "open"
            assert item.milestone is not None

    def test_skips_resolved_findings(self, db: Session):
        org = _seed_org(db)
        assessment = _seed_assessment(db, org)
        _seed_findings(db, assessment, count=2)

        # Mark one finding as resolved
        resolved = Finding(
            assessment_id=assessment.id,
            practice_id="AC.L2-3.1.99",
            finding_type="observation",
            severity="low",
            title="Already Resolved",
            status="resolved",
        )
        db.add(resolved)
        db.flush()

        poam = create_poam(db, org_id=org.id, title="Auto-gen", assessment_id=assessment.id)
        items = generate_from_assessment(db, poam.id, assessment.id)

        assert len(items) == 2  # Only open findings

    def test_rejects_completed_poam(self, db: Session):
        org = _seed_org(db)
        assessment = _seed_assessment(db, org)
        poam = create_poam(db, org_id=org.id, title="Done")
        activate_poam(db, poam.id)
        complete_poam(db, poam.id)

        with pytest.raises(ConflictError):
            generate_from_assessment(db, poam.id, assessment.id)

    def test_no_findings_returns_empty(self, db: Session):
        org = _seed_org(db)
        assessment = _seed_assessment(db, org)
        poam = create_poam(db, org_id=org.id, title="Empty")

        items = generate_from_assessment(db, poam.id, assessment.id)
        assert items == []


# ---------------------------------------------------------------------------
# Overdue detection
# ---------------------------------------------------------------------------


class TestOverdueItems:
    def test_detects_overdue(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")

        # Past due
        add_item(
            db,
            poam.id,
            milestone="Overdue Task",
            scheduled_completion=date.today() - timedelta(days=10),
        )
        # Future due
        add_item(
            db,
            poam.id,
            milestone="Future Task",
            scheduled_completion=date.today() + timedelta(days=30),
        )
        # No due date
        add_item(db, poam.id, milestone="No Date")

        overdue = get_overdue_items(db, poam.id)
        assert len(overdue) == 1
        assert overdue[0].milestone == "Overdue Task"

    def test_completed_items_not_overdue(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Plan")

        item = add_item(
            db,
            poam.id,
            milestone="Done Task",
            scheduled_completion=date.today() - timedelta(days=5),
        )
        update_item(db, item.id, status="in_progress")
        update_item(db, item.id, status="completed")

        overdue = get_overdue_items(db, poam.id)
        assert len(overdue) == 0

    def test_empty_poam(self, db: Session):
        org = _seed_org(db)
        poam = create_poam(db, org_id=org.id, title="Empty")
        overdue = get_overdue_items(db, poam.id)
        assert overdue == []
