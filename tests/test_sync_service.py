"""Tests for DataPact sync service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.datapact import DataPactPracticeMapping, DataPactSyncLog
from cmmc.models.organization import Organization
from cmmc.services.datapact_client import (
    DataPactAuthError,
    DataPactConnectionError,
    DataPactNotFoundError,
)
from cmmc.services.sync_service import sync_assessment, sync_practice

COMPLIANCE_RESPONSE = {
    "contract_id": "c1",
    "status": "compliant",
    "score": 95.0,
    "details": {"total_clauses": 10, "compliant": 9, "non_compliant": 1},
}


@pytest.fixture
def seed_sync(db: Session):
    """Seed org, assessment, practices, and mappings for sync tests."""
    org = Organization(
        id="org1",
        name="Acme Corp",
        datapact_api_url="http://datapact.test:8180",
        datapact_api_key="org-key-123",
    )
    db.add(org)

    domain = CMMCDomain(id="d_ac", domain_id="AC", name="Access Control")
    db.add(domain)

    p1 = CMMCPractice(
        id="cp1", practice_id="AC.L1-3.1.1", domain_ref="AC", level=1,
        title="Authorized Access Control",
    )
    p2 = CMMCPractice(
        id="cp2", practice_id="AC.L1-3.1.2", domain_ref="AC", level=1,
        title="Transaction Control",
    )
    db.add_all([p1, p2])

    assessment = Assessment(
        id="a1", org_id="org1", title="Acme L1 Assessment",
        target_level=1, assessment_type="self", status="in_progress",
    )
    db.add(assessment)
    db.flush()

    ap1 = AssessmentPractice(
        id="ap1", assessment_id="a1", practice_id="AC.L1-3.1.1",
        status="not_evaluated",
    )
    ap2 = AssessmentPractice(
        id="ap2", assessment_id="a1", practice_id="AC.L1-3.1.2",
        status="not_evaluated",
    )
    db.add_all([ap1, ap2])

    # Only ap1 has a mapping
    mapping = DataPactPracticeMapping(
        id="m1", org_id="org1", practice_id="AC.L1-3.1.1",
        datapact_contract_id="c1", datapact_contract_name="Alpha Contract",
    )
    db.add(mapping)
    db.commit()

    return {
        "org": org,
        "assessment": assessment,
        "ap1": ap1,
        "ap2": ap2,
        "mapping": mapping,
    }


# ── sync_practice ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_practice_success(db: Session, seed_sync):
    mock_client = AsyncMock()
    mock_client.get_contract_compliance.return_value = COMPLIANCE_RESPONSE

    result = await sync_practice(db, "a1", "AC.L1-3.1.1", client=mock_client)

    assert result["status"] == "success"
    assert result["practice_id"] == "AC.L1-3.1.1"

    # Verify assessment practice updated
    ap = db.query(AssessmentPractice).filter_by(id="ap1").first()
    assert ap.datapact_sync_status == "synced"
    assert ap.datapact_sync_at is not None

    # Verify sync log created
    log = db.query(DataPactSyncLog).first()
    assert log is not None
    assert log.status == "success"
    assert log.practice_id == "AC.L1-3.1.1"
    assert log.assessment_id == "a1"


@pytest.mark.asyncio
async def test_sync_practice_no_mapping(db: Session, seed_sync):
    """Practice without mapping should return skipped status."""
    mock_client = AsyncMock()

    result = await sync_practice(db, "a1", "AC.L1-3.1.2", client=mock_client)

    assert result["status"] == "skipped"
    assert "no mapping" in result["message"].lower()
    mock_client.get_contract_compliance.assert_not_called()


@pytest.mark.asyncio
async def test_sync_practice_api_error(db: Session, seed_sync):
    mock_client = AsyncMock()
    mock_client.get_contract_compliance.side_effect = DataPactConnectionError(
        "Connection timed out"
    )

    result = await sync_practice(db, "a1", "AC.L1-3.1.1", client=mock_client)

    assert result["status"] == "error"
    assert "timed out" in result["message"].lower()

    # Verify assessment practice marked as error
    ap = db.query(AssessmentPractice).filter_by(id="ap1").first()
    assert ap.datapact_sync_status == "error"

    # Verify error logged
    log = db.query(DataPactSyncLog).first()
    assert log.status == "error"
    assert "timed out" in log.error_message.lower()


@pytest.mark.asyncio
async def test_sync_practice_auth_error(db: Session, seed_sync):
    mock_client = AsyncMock()
    mock_client.get_contract_compliance.side_effect = DataPactAuthError(
        "401 Unauthorized", status_code=401
    )

    result = await sync_practice(db, "a1", "AC.L1-3.1.1", client=mock_client)

    assert result["status"] == "error"
    log = db.query(DataPactSyncLog).first()
    assert log.status == "error"


@pytest.mark.asyncio
async def test_sync_practice_not_found_error(db: Session, seed_sync):
    mock_client = AsyncMock()
    mock_client.get_contract_compliance.side_effect = DataPactNotFoundError(
        "Contract not found", status_code=404
    )

    result = await sync_practice(db, "a1", "AC.L1-3.1.1", client=mock_client)

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_sync_practice_invalid_assessment(db: Session, seed_sync):
    mock_client = AsyncMock()

    result = await sync_practice(db, "bad-id", "AC.L1-3.1.1", client=mock_client)

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_sync_practice_logs_request_payload(db: Session, seed_sync):
    mock_client = AsyncMock()
    mock_client.get_contract_compliance.return_value = COMPLIANCE_RESPONSE

    await sync_practice(db, "a1", "AC.L1-3.1.1", client=mock_client)

    log = db.query(DataPactSyncLog).first()
    assert log.request_payload is not None
    assert log.request_payload["contract_id"] == "c1"
    assert log.response_payload is not None


@pytest.mark.asyncio
async def test_sync_practice_multiple_mappings(db: Session, seed_sync):
    """If a practice maps to multiple contracts, sync uses the first mapping."""
    # Add a second mapping for same practice
    m2 = DataPactPracticeMapping(
        id="m2", org_id="org1", practice_id="AC.L1-3.1.1",
        datapact_contract_id="c2", datapact_contract_name="Beta Contract",
    )
    db.add(m2)
    db.commit()

    mock_client = AsyncMock()
    mock_client.get_contract_compliance.return_value = COMPLIANCE_RESPONSE

    result = await sync_practice(db, "a1", "AC.L1-3.1.1", client=mock_client)

    assert result["status"] == "success"
    # Should have been called (at least once for the first mapping)
    mock_client.get_contract_compliance.assert_called()


# ── sync_assessment ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_assessment_success(db: Session, seed_sync):
    mock_client = AsyncMock()
    mock_client.get_contract_compliance.return_value = COMPLIANCE_RESPONSE

    results = await sync_assessment(db, "a1", client=mock_client)

    # ap1 has mapping → success; ap2 has no mapping → skipped
    assert len(results) == 2
    statuses = {r["practice_id"]: r["status"] for r in results}
    assert statuses["AC.L1-3.1.1"] == "success"
    assert statuses["AC.L1-3.1.2"] == "skipped"


@pytest.mark.asyncio
async def test_sync_assessment_partial_failure(db: Session, seed_sync):
    """One practice failing should not stop others from syncing."""
    # Add mapping for ap2 too
    m2 = DataPactPracticeMapping(
        id="m2", org_id="org1", practice_id="AC.L1-3.1.2",
        datapact_contract_id="c2",
    )
    db.add(m2)
    db.commit()

    mock_client = AsyncMock()
    # First call succeeds, second fails
    mock_client.get_contract_compliance.side_effect = [
        COMPLIANCE_RESPONSE,
        DataPactConnectionError("timeout"),
    ]

    results = await sync_assessment(db, "a1", client=mock_client)

    assert len(results) == 2
    statuses = {r["practice_id"]: r["status"] for r in results}
    # One should succeed, one should error
    assert "success" in statuses.values()
    assert "error" in statuses.values()


@pytest.mark.asyncio
async def test_sync_assessment_invalid_id(db: Session, seed_sync):
    mock_client = AsyncMock()

    results = await sync_assessment(db, "nonexistent", client=mock_client)

    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "not found" in results[0]["message"].lower()


@pytest.mark.asyncio
async def test_sync_assessment_creates_client_from_org(db: Session, seed_sync):
    """When no client passed, should create one from org settings."""
    with patch("cmmc.services.sync_service.DataPactClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get_contract_compliance.return_value = COMPLIANCE_RESPONSE
        MockClient.return_value = mock_instance

        results = await sync_assessment(db, "a1")

        MockClient.assert_called_once_with(
            base_url="http://datapact.test:8180",
            api_key="org-key-123",
        )
        assert any(r["status"] == "success" for r in results)
