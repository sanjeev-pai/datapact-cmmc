"""Dashboard API — compliance summaries, SPRS, timeline, findings."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user
from cmmc.models.user import User
from cmmc.services.dashboard_service import (
    get_assessment_timeline,
    get_compliance_summary,
    get_domain_compliance,
    get_findings_summary,
    get_sprs_summary,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# GET /summary — org compliance overview (scoped to current user's org)
# ---------------------------------------------------------------------------

@router.get("/summary")
def summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Overall compliance % by level for the user's organization."""
    org_id = user.org_id or ""
    return get_compliance_summary(db, org_id)


# ---------------------------------------------------------------------------
# GET /domain-compliance/{assessment_id}
# ---------------------------------------------------------------------------

@router.get("/domain-compliance/{assessment_id}")
def domain_compliance(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-domain compliance scores for a specific assessment."""
    return get_domain_compliance(db, assessment_id)


# ---------------------------------------------------------------------------
# GET /sprs-history/{org_id}
# ---------------------------------------------------------------------------

@router.get("/sprs-history/{org_id}")
def sprs_history(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current + historical SPRS scores for an organization."""
    return get_sprs_summary(db, org_id)


# ---------------------------------------------------------------------------
# GET /timeline/{org_id}
# ---------------------------------------------------------------------------

@router.get("/timeline/{org_id}")
def timeline(
    org_id: str,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recent assessments for an organization, newest first."""
    return get_assessment_timeline(db, org_id, limit=limit)


# ---------------------------------------------------------------------------
# GET /findings-summary/{assessment_id}
# ---------------------------------------------------------------------------

@router.get("/findings-summary/{assessment_id}")
def findings_summary(
    assessment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Findings counts by severity and status for an assessment."""
    return get_findings_summary(db, assessment_id)
