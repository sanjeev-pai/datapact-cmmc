"""Practice evaluation business logic — evaluate, list, and get practice evaluations."""

from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.assessment import Assessment, AssessmentPractice


def _get_assessment(db: Session, assessment_id: str) -> Assessment:
    """Fetch assessment or raise NotFoundError."""
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")
    return assessment


def _get_assessment_practice(
    db: Session, assessment_id: str, practice_id: str
) -> AssessmentPractice:
    """Fetch a single assessment_practice row or raise NotFoundError."""
    ap = (
        db.query(AssessmentPractice)
        .filter_by(assessment_id=assessment_id, practice_id=practice_id)
        .first()
    )
    if not ap:
        raise NotFoundError(
            f"Practice {practice_id} not found in assessment {assessment_id}"
        )
    return ap


def evaluate_practice(
    db: Session,
    assessment_id: str,
    practice_id: str,
    *,
    status: str | None = None,
    score: float | None = None,
    assessor_notes: str | None = None,
) -> AssessmentPractice:
    """Update an assessment practice's evaluation fields.

    Only allowed when the parent assessment is in_progress.
    """
    assessment = _get_assessment(db, assessment_id)

    if assessment.status != "in_progress":
        raise ConflictError(
            "Practices can only be evaluated when the assessment is in_progress"
        )

    ap = _get_assessment_practice(db, assessment_id, practice_id)

    if status is not None:
        ap.status = status
    if score is not None:
        ap.score = score
    if assessor_notes is not None:
        ap.assessor_notes = assessor_notes

    db.flush()

    # Auto-recalculate assessment scores after evaluation change
    from cmmc.services.scoring_service import (
        calculate_overall_score,
        calculate_sprs_score,
    )

    assessment.sprs_score = calculate_sprs_score(db, assessment_id)
    assessment.overall_score = calculate_overall_score(db, assessment_id)

    db.flush()
    db.commit()
    return ap


def get_practice_evaluations(
    db: Session,
    assessment_id: str,
    *,
    status: str | None = None,
    domain: str | None = None,
) -> list[AssessmentPractice]:
    """List all practice evaluations for an assessment with optional filters."""
    _get_assessment(db, assessment_id)  # validate assessment exists

    query = db.query(AssessmentPractice).filter_by(assessment_id=assessment_id)

    if status:
        query = query.filter(AssessmentPractice.status == status)

    if domain:
        query = query.filter(AssessmentPractice.practice_id.startswith(f"{domain}."))

    return query.order_by(AssessmentPractice.practice_id).all()


def get_practice_evaluation(
    db: Session, assessment_id: str, practice_id: str
) -> AssessmentPractice:
    """Get a single practice evaluation."""
    _get_assessment(db, assessment_id)  # validate assessment exists
    return _get_assessment_practice(db, assessment_id, practice_id)
