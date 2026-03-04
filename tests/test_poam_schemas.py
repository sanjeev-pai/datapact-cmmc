"""Tests for POA&M Pydantic schemas."""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from cmmc.schemas.poam import (
    POAMCreate,
    POAMDetailResponse,
    POAMItemCreate,
    POAMItemResponse,
    POAMItemUpdate,
    POAMListResponse,
    POAMResponse,
    POAMUpdate,
)


# ---------------------------------------------------------------------------
# POAMCreate
# ---------------------------------------------------------------------------


class TestPOAMCreate:
    def test_valid_minimal(self):
        data = POAMCreate(org_id="org1", title="Remediation Plan Q1")
        assert data.org_id == "org1"
        assert data.title == "Remediation Plan Q1"
        assert data.assessment_id is None

    def test_valid_with_assessment(self):
        data = POAMCreate(
            org_id="org1", title="Post-Assessment POA&M", assessment_id="a1"
        )
        assert data.assessment_id == "a1"

    def test_rejects_empty_org_id(self):
        with pytest.raises(ValidationError):
            POAMCreate(org_id="", title="Test")

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            POAMCreate(org_id="org1", title="")

    def test_rejects_title_too_long(self):
        with pytest.raises(ValidationError):
            POAMCreate(org_id="org1", title="x" * 257)


# ---------------------------------------------------------------------------
# POAMUpdate
# ---------------------------------------------------------------------------


class TestPOAMUpdate:
    def test_all_fields_optional(self):
        data = POAMUpdate()
        assert data.title is None
        assert data.status is None

    def test_partial_update_title(self):
        data = POAMUpdate(title="Updated Title")
        assert data.title == "Updated Title"
        assert data.status is None

    def test_valid_status_values(self):
        for s in ("draft", "active", "completed"):
            data = POAMUpdate(status=s)
            assert data.status == s

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            POAMUpdate(status="cancelled")

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            POAMUpdate(title="")


# ---------------------------------------------------------------------------
# POAMResponse
# ---------------------------------------------------------------------------


class TestPOAMResponse:
    def test_serializes_all_fields(self):
        now = datetime.now(timezone.utc)
        data = POAMResponse(
            id="p1",
            org_id="org1",
            assessment_id="a1",
            title="Test POA&M",
            status="draft",
            created_at=now,
            updated_at=now,
        )
        assert data.id == "p1"
        assert data.status == "draft"
        assert data.assessment_id == "a1"

    def test_nullable_assessment_id(self):
        now = datetime.now(timezone.utc)
        data = POAMResponse(
            id="p1",
            org_id="org1",
            assessment_id=None,
            title="Standalone POA&M",
            status="active",
            created_at=now,
            updated_at=now,
        )
        assert data.assessment_id is None


# ---------------------------------------------------------------------------
# POAMDetailResponse
# ---------------------------------------------------------------------------


class TestPOAMDetailResponse:
    def test_with_items(self):
        now = datetime.now(timezone.utc)
        item = POAMItemResponse(
            id="pi1",
            poam_id="p1",
            finding_id=None,
            practice_id="AC.L2-3.1.5",
            milestone="Implement MFA",
            scheduled_completion=date(2026, 6, 30),
            actual_completion=None,
            status="open",
            resources_required=None,
            risk_accepted=False,
            created_at=now,
            updated_at=now,
        )
        data = POAMDetailResponse(
            id="p1",
            org_id="org1",
            assessment_id="a1",
            title="Test",
            status="active",
            created_at=now,
            updated_at=now,
            items=[item],
        )
        assert len(data.items) == 1
        assert data.items[0].practice_id == "AC.L2-3.1.5"

    def test_empty_items(self):
        now = datetime.now(timezone.utc)
        data = POAMDetailResponse(
            id="p1",
            org_id="org1",
            title="Empty",
            status="draft",
            created_at=now,
            updated_at=now,
        )
        assert data.items == []


# ---------------------------------------------------------------------------
# POAMListResponse
# ---------------------------------------------------------------------------


class TestPOAMListResponse:
    def test_wraps_list(self):
        now = datetime.now(timezone.utc)
        item = POAMResponse(
            id="p1",
            org_id="org1",
            title="Test",
            status="draft",
            created_at=now,
            updated_at=now,
        )
        data = POAMListResponse(items=[item], total=1)
        assert data.total == 1
        assert len(data.items) == 1

    def test_empty_list(self):
        data = POAMListResponse(items=[], total=0)
        assert data.total == 0
        assert data.items == []


# ---------------------------------------------------------------------------
# POAMItemCreate
# ---------------------------------------------------------------------------


class TestPOAMItemCreate:
    def test_valid_minimal(self):
        data = POAMItemCreate()
        assert data.finding_id is None
        assert data.practice_id is None
        assert data.milestone is None
        assert data.scheduled_completion is None
        assert data.resources_required is None
        assert data.risk_accepted is False

    def test_valid_with_all_fields(self):
        data = POAMItemCreate(
            finding_id="f1",
            practice_id="AC.L2-3.1.5",
            milestone="Deploy MFA solution",
            scheduled_completion=date(2026, 6, 30),
            resources_required="Security team, $5000 budget",
            risk_accepted=False,
        )
        assert data.finding_id == "f1"
        assert data.practice_id == "AC.L2-3.1.5"
        assert data.scheduled_completion == date(2026, 6, 30)

    def test_rejects_practice_id_too_long(self):
        with pytest.raises(ValidationError):
            POAMItemCreate(practice_id="x" * 33)

    def test_rejects_milestone_too_long(self):
        with pytest.raises(ValidationError):
            POAMItemCreate(milestone="x" * 257)


# ---------------------------------------------------------------------------
# POAMItemUpdate
# ---------------------------------------------------------------------------


class TestPOAMItemUpdate:
    def test_all_fields_optional(self):
        data = POAMItemUpdate()
        assert data.milestone is None
        assert data.status is None
        assert data.risk_accepted is None

    def test_valid_status_values(self):
        for s in ("open", "in_progress", "completed"):
            data = POAMItemUpdate(status=s)
            assert data.status == s

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            POAMItemUpdate(status="cancelled")

    def test_set_actual_completion(self):
        data = POAMItemUpdate(
            actual_completion=date(2026, 3, 15), status="completed"
        )
        assert data.actual_completion == date(2026, 3, 15)

    def test_set_risk_accepted(self):
        data = POAMItemUpdate(risk_accepted=True)
        assert data.risk_accepted is True


# ---------------------------------------------------------------------------
# POAMItemResponse
# ---------------------------------------------------------------------------


class TestPOAMItemResponse:
    def test_serializes_all_fields(self):
        now = datetime.now(timezone.utc)
        data = POAMItemResponse(
            id="pi1",
            poam_id="p1",
            finding_id="f1",
            practice_id="AC.L2-3.1.5",
            milestone="Implement MFA",
            scheduled_completion=date(2026, 6, 30),
            actual_completion=date(2026, 5, 20),
            status="completed",
            resources_required="Security team",
            risk_accepted=False,
            created_at=now,
            updated_at=now,
        )
        assert data.id == "pi1"
        assert data.finding_id == "f1"
        assert data.actual_completion == date(2026, 5, 20)
        assert data.risk_accepted is False

    def test_nullable_fields(self):
        now = datetime.now(timezone.utc)
        data = POAMItemResponse(
            id="pi1",
            poam_id="p1",
            finding_id=None,
            practice_id=None,
            milestone=None,
            scheduled_completion=None,
            actual_completion=None,
            status="open",
            resources_required=None,
            risk_accepted=False,
            created_at=now,
            updated_at=now,
        )
        assert data.finding_id is None
        assert data.practice_id is None
        assert data.scheduled_completion is None
