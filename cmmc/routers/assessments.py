"""Assessment CRUD API endpoints with status lifecycle transitions."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.errors import ForbiddenError
from cmmc.models.user import User
from cmmc.schemas.assessment import (
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentResponse,
    AssessmentUpdate,
)
from cmmc.services import assessment_service

router = APIRouter(prefix="/api/assessments", tags=["assessments"])

# Roles that may manage assessments
_MANAGE_ROLES = ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead")


def _check_org_access(user: User, org_id: str) -> None:
    """Raise ForbiddenError if user cannot access the given org's assessments."""
    user_roles = {r.name for r in user.roles}
    if "system_admin" in user_roles:
        return  # system admins can access any org
    if user.org_id != org_id:
        raise ForbiddenError("Access denied to this organization's assessments")


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------

@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: AssessmentCreate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Create a new assessment. Populates practices for the target level."""
    _check_org_access(user, body.org_id)
    return assessment_service.create_assessment(
        db,
        org_id=body.org_id,
        title=body.title,
        target_level=body.target_level,
        assessment_type=body.assessment_type,
        lead_assessor_id=body.lead_assessor_id,
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@router.get("/", response_model=AssessmentListResponse)
def list_assessments(
    org_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    target_level: int | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List assessments. Non-admins see only their org's assessments."""
    user_roles = {r.name for r in user.roles}

    # Determine which org to query
    if "system_admin" in user_roles:
        effective_org_id = org_id  # admin can filter by org or see all
    else:
        effective_org_id = user.org_id  # non-admin always scoped to own org

    if not effective_org_id:
        return AssessmentListResponse(items=[], total=0)

    items, total = assessment_service.list_assessments(
        db,
        org_id=effective_org_id,
        status=status_filter,
        target_level=target_level,
    )
    return AssessmentListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get assessment detail."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return assessment


# ---------------------------------------------------------------------------
# PATCH /{id}
# ---------------------------------------------------------------------------

@router.patch("/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    assessment_id: str,
    body: AssessmentUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Update assessment fields. Cannot update completed assessments."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return assessment_service.update_assessment(
        db,
        assessment_id,
        **body.model_dump(exclude_unset=True),
    )


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------

@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete a draft assessment."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    assessment_service.delete_assessment(db, assessment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

@router.post("/{assessment_id}/start", response_model=AssessmentResponse)
def start_assessment(
    assessment_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Transition draft -> in_progress."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return assessment_service.start_assessment(db, assessment_id)


@router.post("/{assessment_id}/submit", response_model=AssessmentResponse)
def submit_assessment(
    assessment_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Transition in_progress -> under_review."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return assessment_service.submit_assessment(db, assessment_id)


@router.post("/{assessment_id}/complete", response_model=AssessmentResponse)
def complete_assessment(
    assessment_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Transition under_review -> completed."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return assessment_service.complete_assessment(db, assessment_id)
