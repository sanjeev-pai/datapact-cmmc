"""Practice evaluation endpoints nested under assessments."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.errors import ForbiddenError
from cmmc.models.user import User
from cmmc.schemas.assessment import (
    AssessmentPracticeResponse,
    AssessmentPracticeUpdate,
)
from cmmc.services import assessment_service, practice_eval_service

router = APIRouter(prefix="/api/assessments", tags=["assessment-practices"])

_MANAGE_ROLES = ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead")


def _check_org_access(user: User, org_id: str) -> None:
    """Raise ForbiddenError if user cannot access the given org's assessments."""
    user_roles = {r.name for r in user.roles}
    if "system_admin" in user_roles:
        return
    if user.org_id != org_id:
        raise ForbiddenError("Access denied to this organization's assessments")


# ---------------------------------------------------------------------------
# GET /{assessment_id}/practices
# ---------------------------------------------------------------------------

@router.get(
    "/{assessment_id}/practices",
    response_model=list[AssessmentPracticeResponse],
)
def list_practice_evaluations(
    assessment_id: str,
    status: str | None = Query(None),
    domain: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all practice evaluations for an assessment with optional filters."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return practice_eval_service.get_practice_evaluations(
        db, assessment_id, status=status, domain=domain,
    )


# ---------------------------------------------------------------------------
# GET /{assessment_id}/practices/{practice_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{assessment_id}/practices/{practice_id}",
    response_model=AssessmentPracticeResponse,
)
def get_practice_evaluation(
    assessment_id: str,
    practice_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single practice evaluation."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return practice_eval_service.get_practice_evaluation(db, assessment_id, practice_id)


# ---------------------------------------------------------------------------
# PATCH /{assessment_id}/practices/{practice_id}
# ---------------------------------------------------------------------------

@router.patch(
    "/{assessment_id}/practices/{practice_id}",
    response_model=AssessmentPracticeResponse,
)
def update_practice_evaluation(
    assessment_id: str,
    practice_id: str,
    body: AssessmentPracticeUpdate,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Update a practice evaluation (status, score, notes). Only when assessment is in_progress."""
    assessment = assessment_service.get_assessment(db, assessment_id)
    _check_org_access(user, assessment.org_id)
    return practice_eval_service.evaluate_practice(
        db,
        assessment_id,
        practice_id,
        **body.model_dump(exclude_unset=True),
    )
