"""Tests for assessment Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from cmmc.schemas.assessment import (
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentPracticeResponse,
    AssessmentPracticeUpdate,
    AssessmentResponse,
    AssessmentUpdate,
)


# ---------------------------------------------------------------------------
# AssessmentCreate
# ---------------------------------------------------------------------------


class TestAssessmentCreate:
    def test_valid_minimal(self):
        data = AssessmentCreate(
            org_id="org1",
            title="Level 1 Self-Assessment",
            target_level=1,
            assessment_type="self",
        )
        assert data.org_id == "org1"
        assert data.target_level == 1
        assert data.assessment_type == "self"
        assert data.lead_assessor_id is None

    def test_valid_with_all_fields(self):
        data = AssessmentCreate(
            org_id="org1",
            title="Level 2 Third-Party",
            target_level=2,
            assessment_type="third_party",
            lead_assessor_id="user123",
        )
        assert data.lead_assessor_id == "user123"

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            AssessmentCreate(
                org_id="org1", title="", target_level=1, assessment_type="self"
            )

    def test_rejects_target_level_0(self):
        with pytest.raises(ValidationError):
            AssessmentCreate(
                org_id="org1", title="Test", target_level=0, assessment_type="self"
            )

    def test_rejects_target_level_4(self):
        with pytest.raises(ValidationError):
            AssessmentCreate(
                org_id="org1", title="Test", target_level=4, assessment_type="self"
            )

    def test_rejects_invalid_assessment_type(self):
        with pytest.raises(ValidationError):
            AssessmentCreate(
                org_id="org1", title="Test", target_level=1, assessment_type="invalid"
            )

    def test_valid_assessment_types(self):
        for t in ("self", "third_party", "government"):
            data = AssessmentCreate(
                org_id="org1", title="Test", target_level=1, assessment_type=t
            )
            assert data.assessment_type == t


# ---------------------------------------------------------------------------
# AssessmentUpdate
# ---------------------------------------------------------------------------


class TestAssessmentUpdate:
    def test_all_fields_optional(self):
        data = AssessmentUpdate()
        assert data.title is None
        assert data.status is None

    def test_partial_update_title(self):
        data = AssessmentUpdate(title="New Title")
        assert data.title == "New Title"
        assert data.status is None

    def test_valid_status_values(self):
        for s in ("draft", "in_progress", "under_review", "completed"):
            data = AssessmentUpdate(status=s)
            assert data.status == s

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            AssessmentUpdate(status="cancelled")

    def test_rejects_invalid_target_level(self):
        with pytest.raises(ValidationError):
            AssessmentUpdate(target_level=5)


# ---------------------------------------------------------------------------
# AssessmentResponse
# ---------------------------------------------------------------------------


class TestAssessmentResponse:
    def test_serializes_all_fields(self):
        now = datetime.now(timezone.utc)
        data = AssessmentResponse(
            id="a1",
            org_id="org1",
            title="Test Assessment",
            target_level=2,
            assessment_type="self",
            status="draft",
            lead_assessor_id=None,
            started_at=None,
            completed_at=None,
            overall_score=None,
            sprs_score=None,
            created_at=now,
            updated_at=now,
        )
        assert data.id == "a1"
        assert data.status == "draft"
        assert data.created_at == now

    def test_with_scores(self):
        now = datetime.now(timezone.utc)
        data = AssessmentResponse(
            id="a1",
            org_id="org1",
            title="Scored",
            target_level=2,
            assessment_type="third_party",
            status="completed",
            lead_assessor_id="user1",
            started_at=now,
            completed_at=now,
            overall_score=0.85,
            sprs_score=95,
            created_at=now,
            updated_at=now,
        )
        assert data.overall_score == 0.85
        assert data.sprs_score == 95


# ---------------------------------------------------------------------------
# AssessmentListResponse
# ---------------------------------------------------------------------------


class TestAssessmentListResponse:
    def test_wraps_list_with_count(self):
        now = datetime.now(timezone.utc)
        item = AssessmentResponse(
            id="a1",
            org_id="org1",
            title="Test",
            target_level=1,
            assessment_type="self",
            status="draft",
            lead_assessor_id=None,
            started_at=None,
            completed_at=None,
            overall_score=None,
            sprs_score=None,
            created_at=now,
            updated_at=now,
        )
        data = AssessmentListResponse(items=[item], total=1)
        assert data.total == 1
        assert len(data.items) == 1

    def test_empty_list(self):
        data = AssessmentListResponse(items=[], total=0)
        assert data.total == 0
        assert data.items == []


# ---------------------------------------------------------------------------
# AssessmentPracticeUpdate
# ---------------------------------------------------------------------------


class TestAssessmentPracticeUpdate:
    def test_all_fields_optional(self):
        data = AssessmentPracticeUpdate()
        assert data.status is None
        assert data.score is None
        assert data.assessor_notes is None

    def test_valid_practice_statuses(self):
        for s in ("not_evaluated", "met", "not_met", "partially_met", "not_applicable"):
            data = AssessmentPracticeUpdate(status=s)
            assert data.status == s

    def test_rejects_invalid_practice_status(self):
        with pytest.raises(ValidationError):
            AssessmentPracticeUpdate(status="unknown")

    def test_score_range(self):
        data = AssessmentPracticeUpdate(score=0.5)
        assert data.score == 0.5

    def test_rejects_score_above_1(self):
        with pytest.raises(ValidationError):
            AssessmentPracticeUpdate(score=1.5)

    def test_rejects_score_below_0(self):
        with pytest.raises(ValidationError):
            AssessmentPracticeUpdate(score=-0.1)


# ---------------------------------------------------------------------------
# AssessmentPracticeResponse
# ---------------------------------------------------------------------------


class TestAssessmentPracticeResponse:
    def test_serializes_all_fields(self):
        now = datetime.now(timezone.utc)
        data = AssessmentPracticeResponse(
            id="ap1",
            assessment_id="a1",
            practice_id="AC.L1-3.1.1",
            status="met",
            score=1.0,
            assessor_notes="Fully implemented",
            datapact_sync_status="synced",
            datapact_sync_at=now,
            created_at=now,
            updated_at=now,
        )
        assert data.practice_id == "AC.L1-3.1.1"
        assert data.status == "met"
        assert data.datapact_sync_status == "synced"

    def test_nullable_fields(self):
        now = datetime.now(timezone.utc)
        data = AssessmentPracticeResponse(
            id="ap1",
            assessment_id="a1",
            practice_id="AC.L1-3.1.1",
            status="not_evaluated",
            score=None,
            assessor_notes=None,
            datapact_sync_status=None,
            datapact_sync_at=None,
            created_at=now,
            updated_at=now,
        )
        assert data.score is None
        assert data.datapact_sync_status is None
