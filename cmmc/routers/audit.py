"""Audit log API endpoints — read-only access for admins."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import require_role
from cmmc.models.audit import AuditLog
from cmmc.models.user import User
from cmmc.schemas.audit import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/api/audit-log", tags=["audit"])

_ADMIN_ROLES = ("system_admin", "org_admin")


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    user_id: str | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action (create/update/delete)"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """List audit log entries. Admin only."""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AuditLogListResponse(items=items, total=total)


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: str,
    user: User = Depends(require_role(*_ADMIN_ROLES)),
    db: Session = Depends(get_db),
):
    """Get a single audit log entry. Admin only."""
    from cmmc.errors import NotFoundError

    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise NotFoundError(f"Audit log {log_id} not found")
    return log
