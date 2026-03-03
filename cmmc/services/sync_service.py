"""DataPact sync service — sync assessment practices with DataPact compliance data."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.datapact import DataPactPracticeMapping, DataPactSyncLog
from cmmc.models.organization import Organization
from cmmc.services.datapact_client import DataPactClient, DataPactError

logger = logging.getLogger(__name__)

SyncResult = dict[str, Any]


async def sync_practice(
    db: Session,
    assessment_id: str,
    practice_id: str,
    *,
    client: DataPactClient | None = None,
) -> SyncResult:
    """Sync a single assessment practice with DataPact.

    Finds the practice's contract mapping, calls DataPact for compliance data,
    updates the assessment practice sync status, and logs the operation.

    Returns a result dict: ``{practice_id, status, message, ...}``.
    """
    # Find the assessment and its practice
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        return _error_result(practice_id, f"Assessment {assessment_id} not found")

    ap = (
        db.query(AssessmentPractice)
        .filter_by(assessment_id=assessment_id, practice_id=practice_id)
        .first()
    )
    if not ap:
        return _error_result(practice_id, f"AssessmentPractice not found: {practice_id}")

    # Find mapping(s) for this practice + org
    mappings = (
        db.query(DataPactPracticeMapping)
        .filter_by(org_id=assessment.org_id, practice_id=practice_id)
        .all()
    )
    if not mappings:
        return {
            "practice_id": practice_id,
            "status": "skipped",
            "message": "No mapping found for this practice",
        }

    # Resolve client from org settings if not provided
    if client is None:
        client = _build_client(db, assessment.org_id)

    # Sync using the first mapping's contract
    mapping = mappings[0]
    contract_id = mapping.datapact_contract_id

    request_payload = {
        "contract_id": contract_id,
        "practice_id": practice_id,
        "assessment_id": assessment_id,
    }

    try:
        response = await client.get_contract_compliance(contract_id)

        # Update assessment practice
        ap.datapact_sync_status = "synced"
        ap.datapact_sync_at = datetime.now(UTC)

        # Log success
        _create_log(
            db,
            org_id=assessment.org_id,
            assessment_id=assessment_id,
            practice_id=practice_id,
            request_payload=request_payload,
            response_payload=response,
            status="success",
        )

        db.flush()
        db.commit()

        return {
            "practice_id": practice_id,
            "status": "success",
            "message": "Synced successfully",
            "compliance": response,
        }

    except DataPactError as exc:
        # Mark practice as error
        ap.datapact_sync_status = "error"
        ap.datapact_sync_at = datetime.now(UTC)

        _create_log(
            db,
            org_id=assessment.org_id,
            assessment_id=assessment_id,
            practice_id=practice_id,
            request_payload=request_payload,
            response_payload=None,
            status="error",
            error_message=str(exc),
        )

        db.flush()
        db.commit()

        logger.warning("Sync failed for %s: %s", practice_id, exc)
        return _error_result(practice_id, str(exc))


async def sync_assessment(
    db: Session,
    assessment_id: str,
    *,
    client: DataPactClient | None = None,
) -> list[SyncResult]:
    """Sync all practices in an assessment with DataPact.

    Handles partial failures — one practice failing does not stop others.
    Returns a list of results, one per assessment practice.
    """
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        return [_error_result("*", f"Assessment {assessment_id} not found")]

    # Resolve client once for the whole assessment
    if client is None:
        client = _build_client(db, assessment.org_id)

    # Get all practices for this assessment
    practices = (
        db.query(AssessmentPractice)
        .filter_by(assessment_id=assessment_id)
        .order_by(AssessmentPractice.practice_id)
        .all()
    )

    results: list[SyncResult] = []
    for ap in practices:
        result = await sync_practice(
            db, assessment_id, ap.practice_id, client=client
        )
        results.append(result)

    return results


# ── Internal helpers ─────────────────────────────────────────────────────────


def _build_client(db: Session, org_id: str) -> DataPactClient:
    """Create a DataPactClient from org settings, falling back to config defaults."""
    org = db.query(Organization).filter_by(id=org_id).first()
    kwargs: dict[str, Any] = {}
    if org and org.datapact_api_url:
        kwargs["base_url"] = org.datapact_api_url
    if org and org.datapact_api_key:
        kwargs["api_key"] = org.datapact_api_key
    return DataPactClient(**kwargs)


def _create_log(
    db: Session,
    *,
    org_id: str,
    assessment_id: str,
    practice_id: str,
    request_payload: dict | None,
    response_payload: dict | None,
    status: str,
    error_message: str | None = None,
) -> DataPactSyncLog:
    """Create a sync log entry."""
    log = DataPactSyncLog(
        org_id=org_id,
        assessment_id=assessment_id,
        practice_id=practice_id,
        request_payload=request_payload,
        response_payload=response_payload,
        status=status,
        error_message=error_message,
    )
    db.add(log)
    return log


def _error_result(practice_id: str, message: str) -> SyncResult:
    return {
        "practice_id": practice_id,
        "status": "error",
        "message": message,
    }
