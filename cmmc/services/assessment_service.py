"""Assessment business logic — CRUD, status lifecycle, practice population."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCPractice

# Valid status transitions: current_status -> set of allowed next statuses
_TRANSITIONS = {
    "draft": {"in_progress"},
    "in_progress": {"under_review"},
    "under_review": {"completed"},
    "completed": set(),
}


def create_assessment(
    db: Session,
    *,
    org_id: str,
    title: str,
    target_level: int,
    assessment_type: str,
    lead_assessor_id: str | None = None,
) -> Assessment:
    """Create a new assessment in draft status and populate its practices."""
    assessment = Assessment(
        org_id=org_id,
        title=title,
        target_level=target_level,
        assessment_type=assessment_type,
        status="draft",
        lead_assessor_id=lead_assessor_id,
    )
    db.add(assessment)
    db.flush()

    # Populate assessment_practices for all practices at or below target level
    practices = (
        db.query(CMMCPractice)
        .filter(CMMCPractice.level <= target_level)
        .all()
    )
    for practice in practices:
        ap = AssessmentPractice(
            assessment_id=assessment.id,
            practice_id=practice.practice_id,
            status="not_evaluated",
        )
        db.add(ap)

    db.flush()
    db.commit()
    return assessment


def get_assessment(db: Session, assessment_id: str) -> Assessment:
    """Get an assessment by ID. Raises NotFoundError if not found."""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")
    return assessment


def list_assessments(
    db: Session,
    *,
    org_id: str,
    status: str | None = None,
    target_level: int | None = None,
) -> tuple[list[Assessment], int]:
    """List assessments for an org with optional filters. Returns (items, total)."""
    query = db.query(Assessment).filter_by(org_id=org_id)

    if status:
        query = query.filter_by(status=status)
    if target_level is not None:
        query = query.filter_by(target_level=target_level)

    query = query.order_by(Assessment.created_at.desc())
    items = query.all()
    return items, len(items)


def update_assessment(
    db: Session,
    assessment_id: str,
    **kwargs: str | int | None,
) -> Assessment:
    """Update assessment fields. Raises ConflictError if completed."""
    assessment = get_assessment(db, assessment_id)

    if assessment.status == "completed":
        raise ConflictError("Cannot update a completed assessment")

    for key, value in kwargs.items():
        if value is not None and hasattr(assessment, key):
            setattr(assessment, key, value)

    db.flush()
    db.commit()
    return assessment


def delete_assessment(db: Session, assessment_id: str) -> None:
    """Delete a draft assessment. Raises ConflictError if not draft."""
    assessment = get_assessment(db, assessment_id)

    if assessment.status != "draft":
        raise ConflictError("Only draft assessments can be deleted")

    # Delete associated practices first
    db.query(AssessmentPractice).filter_by(assessment_id=assessment_id).delete()
    db.delete(assessment)
    db.flush()
    db.commit()


def _transition(db: Session, assessment_id: str, target_status: str) -> Assessment:
    """Transition assessment to a new status. Raises ConflictError on invalid transition."""
    assessment = get_assessment(db, assessment_id)
    allowed = _TRANSITIONS.get(assessment.status, set())

    if target_status not in allowed:
        raise ConflictError(
            f"Cannot transition from '{assessment.status}' to '{target_status}'"
        )

    assessment.status = target_status

    if target_status == "in_progress":
        assessment.started_at = datetime.now(timezone.utc)
    elif target_status == "completed":
        assessment.completed_at = datetime.now(timezone.utc)

    db.flush()
    db.commit()
    return assessment


def start_assessment(db: Session, assessment_id: str) -> Assessment:
    """Transition draft -> in_progress."""
    return _transition(db, assessment_id, "in_progress")


def submit_assessment(db: Session, assessment_id: str) -> Assessment:
    """Transition in_progress -> under_review."""
    return _transition(db, assessment_id, "under_review")


def complete_assessment(db: Session, assessment_id: str) -> Assessment:
    """Transition under_review -> completed."""
    return _transition(db, assessment_id, "completed")
