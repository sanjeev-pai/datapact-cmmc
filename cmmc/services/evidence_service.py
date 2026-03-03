"""Evidence business logic — upload, retrieve, list, delete, review."""

import os
import shutil
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from cmmc.config import UPLOAD_DIR
from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.assessment import AssessmentPractice
from cmmc.models.evidence import Evidence


def upload_evidence(
    db: Session,
    *,
    assessment_practice_id: str,
    title: str,
    description: str | None = None,
    file_content: bytes | None = None,
    file_name: str | None = None,
    mime_type: str | None = None,
    upload_dir: str | None = None,
) -> Evidence:
    """Create an evidence record, optionally saving a file to disk."""
    # Validate that the assessment practice exists
    ap = db.query(AssessmentPractice).filter_by(id=assessment_practice_id).first()
    if not ap:
        raise NotFoundError(f"Assessment practice {assessment_practice_id} not found")

    evidence = Evidence(
        assessment_practice_id=assessment_practice_id,
        title=title,
        description=description,
        review_status="pending",
    )
    db.add(evidence)
    db.flush()  # generate id

    # Save file to disk if content provided
    if file_content is not None and file_name is not None:
        base_dir = upload_dir or UPLOAD_DIR
        evidence_dir = os.path.join(base_dir, evidence.id)
        os.makedirs(evidence_dir, exist_ok=True)

        file_path = os.path.join(evidence_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(file_content)

        evidence.file_path = file_path
        evidence.file_name = file_name
        evidence.file_size = len(file_content)
        evidence.mime_type = mime_type

    db.flush()
    db.commit()
    return evidence


def get_evidence(db: Session, evidence_id: str) -> Evidence:
    """Get evidence by ID. Raises NotFoundError if not found."""
    evidence = db.query(Evidence).filter_by(id=evidence_id).first()
    if not evidence:
        raise NotFoundError(f"Evidence {evidence_id} not found")
    return evidence


def list_evidence(
    db: Session,
    *,
    assessment_practice_id: str | None = None,
    assessment_id: str | None = None,
    review_status: str | None = None,
) -> tuple[list[Evidence], int]:
    """List evidence with optional filters. Returns (items, total)."""
    query = db.query(Evidence)

    if assessment_practice_id:
        query = query.filter_by(assessment_practice_id=assessment_practice_id)

    if assessment_id:
        # Join through AssessmentPractice to filter by assessment
        query = query.join(AssessmentPractice).filter(
            AssessmentPractice.assessment_id == assessment_id
        )

    if review_status:
        query = query.filter_by(review_status=review_status)

    query = query.order_by(Evidence.created_at.desc())
    items = query.all()
    return items, len(items)


def delete_evidence(db: Session, evidence_id: str) -> None:
    """Delete evidence. Only pending evidence can be deleted."""
    evidence = get_evidence(db, evidence_id)

    if evidence.review_status != "pending":
        raise ConflictError("Only pending evidence can be deleted")

    # Remove file from disk if it exists
    if evidence.file_path and os.path.exists(evidence.file_path):
        evidence_dir = os.path.dirname(evidence.file_path)
        shutil.rmtree(evidence_dir, ignore_errors=True)

    db.delete(evidence)
    db.flush()
    db.commit()


def review_evidence(
    db: Session,
    evidence_id: str,
    *,
    reviewer_id: str,
    review_status: str,
) -> Evidence:
    """Review evidence (accept or reject). Only pending evidence can be reviewed."""
    evidence = get_evidence(db, evidence_id)

    if evidence.review_status != "pending":
        raise ConflictError(
            f"Evidence already reviewed (status: {evidence.review_status})"
        )

    evidence.review_status = review_status
    evidence.reviewer_id = reviewer_id
    evidence.reviewed_at = datetime.now(timezone.utc)

    db.flush()
    db.commit()
    return evidence
