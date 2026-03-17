"""Unified audit service — merges CMMC and DataPact audit logs."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from cmmc.models.audit import AuditLog
from cmmc.models.organization import Organization
from cmmc.schemas.audit import UnifiedAuditEntry, UnifiedAuditResponse
from cmmc.services.datapact_client import DataPactClient, DataPactError

logger = logging.getLogger(__name__)


def _build_client(org: Organization) -> DataPactClient | None:
    """Build a DataPactClient from org settings, or None if not configured."""
    if not org.datapact_api_url:
        return None
    kwargs: dict[str, Any] = {"base_url": org.datapact_api_url}
    if org.datapact_api_key:
        kwargs["api_key"] = org.datapact_api_key
    return DataPactClient(**kwargs)


def _cmmc_to_unified(log: AuditLog) -> UnifiedAuditEntry:
    """Convert a local AuditLog row to a UnifiedAuditEntry."""
    return UnifiedAuditEntry(
        id=log.id,
        source="cmmc",
        user_id=log.user_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        details=log.details,
        ip_address=log.ip_address,
        created_at=log.created_at,
    )


def _datapact_to_unified(entry: dict[str, Any]) -> UnifiedAuditEntry:
    """Convert a DataPact audit entry dict to a UnifiedAuditEntry."""
    created = entry.get("created_at") or entry.get("timestamp") or entry.get("date")
    if isinstance(created, str):
        # Parse ISO format; append UTC if naive
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.now(timezone.utc)
    elif isinstance(created, datetime):
        dt = created
    else:
        dt = datetime.now(timezone.utc)

    return UnifiedAuditEntry(
        id=f"dp-{entry.get('id', 'unknown')}",
        source="datapact",
        user_id=entry.get("user_id") or entry.get("actor_id"),
        action=entry.get("action", "unknown"),
        resource_type=entry.get("resource_type") or entry.get("entity_type") or "unknown",
        resource_id=entry.get("resource_id") or entry.get("entity_id"),
        details=entry.get("details") or entry.get("metadata"),
        ip_address=entry.get("ip_address"),
        created_at=dt,
    )


async def get_unified_audit_log(
    db: Session,
    org_id: str,
    *,
    action: str | None = None,
    resource_type: str | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> UnifiedAuditResponse:
    """Fetch and merge audit logs from CMMC and DataPact.

    Entries are sorted by created_at descending (newest first).
    The ``source`` filter restricts to "cmmc" or "datapact" only.
    """
    cmmc_entries: list[UnifiedAuditEntry] = []
    cmmc_total = 0
    dp_entries: list[UnifiedAuditEntry] = []
    dp_total = 0
    dp_available = False

    # ── Local CMMC logs ──────────────────────────────────────────────
    if source in (None, "cmmc"):
        query = db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        cmmc_total = query.count()
        rows = query.order_by(AuditLog.created_at.desc()).all()
        cmmc_entries = [_cmmc_to_unified(r) for r in rows]

    # ── DataPact audit logs ──────────────────────────────────────────
    if source in (None, "datapact"):
        org = db.query(Organization).filter_by(id=org_id).first()
        if org:
            client = _build_client(org)
            if client:
                try:
                    params: dict[str, Any] = {}
                    if action:
                        params["action"] = action
                    if resource_type:
                        params["resource_type"] = resource_type
                    data = await client.get_audit_logs(**params)
                    dp_available = True
                    dp_total = data.get("total", 0)
                    for item in data.get("items", []):
                        dp_entries.append(_datapact_to_unified(item))
                except DataPactError as exc:
                    logger.warning("Failed to fetch DataPact audit logs: %s", exc)

    # ── Merge and sort ───────────────────────────────────────────────
    all_entries = cmmc_entries + dp_entries

    def _sort_key(e: UnifiedAuditEntry) -> datetime:
        """Normalize to UTC-aware for comparison."""
        dt = e.created_at
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    all_entries.sort(key=_sort_key, reverse=True)

    total = len(all_entries)
    page = all_entries[offset : offset + limit]

    return UnifiedAuditResponse(
        items=page,
        total=total,
        cmmc_total=cmmc_total,
        datapact_total=dp_total,
        datapact_available=dp_available,
    )
