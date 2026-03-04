"""Findings API endpoints — CRUD for assessment findings."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.errors import ForbiddenError
from cmmc.models.assessment import Assessment
from cmmc.models.user import User
from cmmc.schemas.finding import (
    FindingCreate,
    FindingListResponse,
    FindingResponse,
    FindingUpdate,
)
from cmmc.services import finding_service

router = APIRouter(prefix="/api/findings", tags=["findings"])

_MANAGE_ROLES = ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead")


def _check_org_access(user: User, org_id: str) -> None:
    user_roles = {r.name for r in user.roles}
    if "system_admin" in user_roles:
        return
    if user.org_id != org_id:
        raise ForbiddenError("Access denied to this organization's findings")


def _get_assessment_org_id(db: Session, assessment_id: str) -> str:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        from cmmc.errors import NotFoundError

        raise NotFoundError("Assessment not found")
    return assessment.org_id


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------


@router.post("", response_model=FindingResponse, status_code=status.HTTP_201_CREATED)
def create_finding(
    body: FindingCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Create a new finding for an assessment."""
    org_id = _get_assessment_org_id(db, body.assessment_id)
    _check_org_access(user, org_id)
    return finding_service.create_finding(
        db,
        assessment_id=body.assessment_id,
        practice_id=body.practice_id,
        finding_type=body.finding_type,
        severity=body.severity,
        title=body.title,
        description=body.description,
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


@router.get("", response_model=FindingListResponse)
def list_findings(
    assessment_id: str | None = Query(None),
    finding_type: str | None = Query(None, alias="type"),
    severity: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    org_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List findings. System admins can filter by org_id; others see own org only."""
    user_roles = {r.name for r in user.roles}

    if "system_admin" in user_roles:
        effective_org_id = org_id  # None → all orgs
    else:
        effective_org_id = user.org_id

    if "system_admin" not in user_roles and not effective_org_id:
        return FindingListResponse(items=[], total=0)

    items, total = finding_service.list_findings(
        db,
        assessment_id=assessment_id,
        finding_type=finding_type,
        severity=severity,
        status=status_filter,
        org_id=effective_org_id,
    )
    return FindingListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a finding by ID."""
    finding = finding_service.get_finding(db, finding_id)
    org_id = _get_assessment_org_id(db, finding.assessment_id)
    _check_org_access(user, org_id)
    return finding


# ---------------------------------------------------------------------------
# PATCH /{id}
# ---------------------------------------------------------------------------


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(
    finding_id: str,
    body: FindingUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Update a finding's fields."""
    finding = finding_service.get_finding(db, finding_id)
    org_id = _get_assessment_org_id(db, finding.assessment_id)
    _check_org_access(user, org_id)
    return finding_service.update_finding(
        db, finding_id, **body.model_dump(exclude_unset=True)
    )


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------


@router.delete("/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_finding(
    finding_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete an open finding."""
    finding = finding_service.get_finding(db, finding_id)
    org_id = _get_assessment_org_id(db, finding.assessment_id)
    _check_org_access(user, org_id)
    finding_service.delete_finding(db, finding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
