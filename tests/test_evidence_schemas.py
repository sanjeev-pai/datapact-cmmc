"""Tests for evidence Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from cmmc.schemas.evidence import (
    EvidenceCreate,
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceReview,
    EvidenceUpdate,
)


# ---------------------------------------------------------------------------
# EvidenceCreate
# ---------------------------------------------------------------------------


class TestEvidenceCreate:
    def test_valid_minimal(self):
        data = EvidenceCreate(
            assessment_practice_id="ap1",
            title="SSP Document",
        )
        assert data.assessment_practice_id == "ap1"
        assert data.title == "SSP Document"
        assert data.description is None
        assert data.file_name is None
        assert data.file_size is None
        assert data.mime_type is None

    def test_valid_with_all_fields(self):
        data = EvidenceCreate(
            assessment_practice_id="ap1",
            title="Network Diagram",
            description="Shows segmentation of CUI network",
            file_name="network_diagram.pdf",
            file_size=204800,
            mime_type="application/pdf",
        )
        assert data.description == "Shows segmentation of CUI network"
        assert data.file_name == "network_diagram.pdf"
        assert data.file_size == 204800
        assert data.mime_type == "application/pdf"

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(assessment_practice_id="ap1", title="")

    def test_rejects_missing_assessment_practice_id(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(title="Some evidence")  # type: ignore[call-arg]

    def test_rejects_title_too_long(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(assessment_practice_id="ap1", title="x" * 257)

    def test_rejects_negative_file_size(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(
                assessment_practice_id="ap1",
                title="Test",
                file_size=-1,
            )

    def test_rejects_zero_file_size(self):
        with pytest.raises(ValidationError):
            EvidenceCreate(
                assessment_practice_id="ap1",
                title="Test",
                file_size=0,
            )


# ---------------------------------------------------------------------------
# EvidenceUpdate
# ---------------------------------------------------------------------------


class TestEvidenceUpdate:
    def test_all_fields_optional(self):
        data = EvidenceUpdate()
        assert data.title is None
        assert data.description is None

    def test_partial_update_title(self):
        data = EvidenceUpdate(title="Updated Title")
        assert data.title == "Updated Title"
        assert data.description is None

    def test_partial_update_description(self):
        data = EvidenceUpdate(description="New description")
        assert data.description == "New description"

    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            EvidenceUpdate(title="")

    def test_rejects_title_too_long(self):
        with pytest.raises(ValidationError):
            EvidenceUpdate(title="x" * 257)


# ---------------------------------------------------------------------------
# EvidenceReview
# ---------------------------------------------------------------------------


class TestEvidenceReview:
    def test_accept(self):
        data = EvidenceReview(review_status="accepted")
        assert data.review_status == "accepted"

    def test_reject(self):
        data = EvidenceReview(review_status="rejected")
        assert data.review_status == "rejected"

    def test_rejects_pending(self):
        with pytest.raises(ValidationError):
            EvidenceReview(review_status="pending")

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            EvidenceReview(review_status="unknown")


# ---------------------------------------------------------------------------
# EvidenceResponse
# ---------------------------------------------------------------------------


class TestEvidenceResponse:
    def test_serializes_all_fields(self):
        now = datetime.now(timezone.utc)
        data = EvidenceResponse(
            id="ev1",
            assessment_practice_id="ap1",
            title="SSP Document",
            description="System security plan",
            file_path="/uploads/ev1/ssp.pdf",
            file_url=None,
            file_name="ssp.pdf",
            file_size=102400,
            mime_type="application/pdf",
            review_status="pending",
            reviewer_id=None,
            reviewed_at=None,
            created_at=now,
            updated_at=now,
        )
        assert data.id == "ev1"
        assert data.title == "SSP Document"
        assert data.review_status == "pending"
        assert data.file_size == 102400

    def test_with_review(self):
        now = datetime.now(timezone.utc)
        data = EvidenceResponse(
            id="ev1",
            assessment_practice_id="ap1",
            title="Policy Doc",
            description=None,
            file_path="/uploads/ev1/policy.pdf",
            file_url=None,
            file_name="policy.pdf",
            file_size=51200,
            mime_type="application/pdf",
            review_status="accepted",
            reviewer_id="user1",
            reviewed_at=now,
            created_at=now,
            updated_at=now,
        )
        assert data.review_status == "accepted"
        assert data.reviewer_id == "user1"
        assert data.reviewed_at == now

    def test_nullable_fields(self):
        now = datetime.now(timezone.utc)
        data = EvidenceResponse(
            id="ev1",
            assessment_practice_id="ap1",
            title="Note",
            description=None,
            file_path=None,
            file_url=None,
            file_name=None,
            file_size=None,
            mime_type=None,
            review_status="pending",
            reviewer_id=None,
            reviewed_at=None,
            created_at=now,
            updated_at=now,
        )
        assert data.file_path is None
        assert data.file_name is None
        assert data.file_size is None
        assert data.mime_type is None


# ---------------------------------------------------------------------------
# EvidenceListResponse
# ---------------------------------------------------------------------------


class TestEvidenceListResponse:
    def test_wraps_list_with_count(self):
        now = datetime.now(timezone.utc)
        item = EvidenceResponse(
            id="ev1",
            assessment_practice_id="ap1",
            title="Test",
            description=None,
            file_path=None,
            file_url=None,
            file_name=None,
            file_size=None,
            mime_type=None,
            review_status="pending",
            reviewer_id=None,
            reviewed_at=None,
            created_at=now,
            updated_at=now,
        )
        data = EvidenceListResponse(items=[item], total=1)
        assert data.total == 1
        assert len(data.items) == 1

    def test_empty_list(self):
        data = EvidenceListResponse(items=[], total=0)
        assert data.total == 0
        assert data.items == []
