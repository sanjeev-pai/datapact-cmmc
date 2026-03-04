"""POA&M API endpoints — CRUD, status transitions, items, auto-generation."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.errors import ForbiddenError
from cmmc.models.user import User
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
from cmmc.services import poam_service

router = APIRouter(prefix="/api/poams", tags=["poams"])

_MANAGE_ROLES = ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead")


def _check_org_access(user: User, org_id: str) -> None:
    user_roles = {r.name for r in user.roles}
    if "system_admin" in user_roles:
        return
    if user.org_id != org_id:
        raise ForbiddenError("Access denied to this organization's POA&Ms")


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------

@router.post("", response_model=POAMResponse, status_code=status.HTTP_201_CREATED)
def create_poam(
    body: POAMCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Create a new POA&M in draft status."""
    _check_org_access(user, body.org_id)
    return poam_service.create_poam(
        db,
        org_id=body.org_id,
        title=body.title,
        assessment_id=body.assessment_id,
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@router.get("", response_model=POAMListResponse)
def list_poams(
    org_id: str | None = Query(None),
    assessment_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List POA&Ms. Non-admins see only their org's POA&Ms."""
    user_roles = {r.name for r in user.roles}

    if "system_admin" in user_roles:
        effective_org_id = org_id
    else:
        effective_org_id = user.org_id

    if "system_admin" not in user_roles and not effective_org_id:
        return POAMListResponse(items=[], total=0)

    items, total = poam_service.list_poams(
        db,
        org_id=effective_org_id,
        assessment_id=assessment_id,
        status=status_filter,
    )
    return POAMListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------

@router.get("/{poam_id}", response_model=POAMDetailResponse)
def get_poam(
    poam_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get POA&M detail with items."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam


# ---------------------------------------------------------------------------
# PATCH /{id}
# ---------------------------------------------------------------------------

@router.patch("/{poam_id}", response_model=POAMResponse)
def update_poam(
    poam_id: str,
    body: POAMUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Update POA&M fields. Cannot update completed POA&Ms."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam_service.update_poam(
        db, poam_id, **body.model_dump(exclude_unset=True)
    )


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------

@router.delete("/{poam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poam(
    poam_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete a draft POA&M."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    poam_service.delete_poam(db, poam_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

@router.post("/{poam_id}/activate", response_model=POAMResponse)
def activate_poam(
    poam_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Transition draft -> active."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam_service.activate_poam(db, poam_id)


@router.post("/{poam_id}/complete", response_model=POAMResponse)
def complete_poam(
    poam_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Transition active -> completed."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam_service.complete_poam(db, poam_id)


# ---------------------------------------------------------------------------
# Item endpoints
# ---------------------------------------------------------------------------

@router.post("/{poam_id}/items", response_model=POAMItemResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    poam_id: str,
    body: POAMItemCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Add an item to a POA&M."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam_service.add_item(
        db,
        poam_id,
        finding_id=body.finding_id,
        practice_id=body.practice_id,
        milestone=body.milestone,
        scheduled_completion=body.scheduled_completion,
        resources_required=body.resources_required,
        risk_accepted=body.risk_accepted,
    )


@router.patch("/{poam_id}/items/{item_id}", response_model=POAMItemResponse)
def update_item(
    poam_id: str,
    item_id: str,
    body: POAMItemUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Update a POA&M item."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam_service.update_item(
        db, item_id, **body.model_dump(exclude_unset=True)
    )


@router.delete("/{poam_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    poam_id: str,
    item_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Remove a POA&M item."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    poam_service.remove_item(db, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Auto-generation
# ---------------------------------------------------------------------------

@router.post("/generate/{assessment_id}", response_model=list[POAMItemResponse])
def generate_from_assessment(
    assessment_id: str,
    poam_id: str = Query(..., description="POA&M to generate items into"),
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Auto-generate POA&M items from unresolved assessment findings."""
    poam = poam_service.get_poam(db, poam_id)
    _check_org_access(user, poam.org_id)
    return poam_service.generate_from_assessment(db, poam_id, assessment_id)
