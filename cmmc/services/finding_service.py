"""Finding business logic — CRUD for assessment findings."""

from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.assessment import Assessment
from cmmc.models.finding import Finding


def _get_or_404(db: Session, finding_id: str) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise NotFoundError("Finding not found")
    return finding


def create_finding(
    db: Session,
    *,
    assessment_id: str,
    finding_type: str,
    severity: str,
    title: str,
    practice_id: str | None = None,
    description: str | None = None,
) -> Finding:
    """Create a new finding linked to an assessment."""
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise NotFoundError("Assessment not found")

    finding = Finding(
        assessment_id=assessment_id,
        practice_id=practice_id,
        finding_type=finding_type,
        severity=severity,
        title=title,
        description=description,
        status="open",
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def get_finding(db: Session, finding_id: str) -> Finding:
    """Get a single finding by ID."""
    return _get_or_404(db, finding_id)


def list_findings(
    db: Session,
    *,
    assessment_id: str | None = None,
    finding_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    org_id: str | None = None,
) -> tuple[list[Finding], int]:
    """List findings with optional filters. Returns (items, total)."""
    q = db.query(Finding)

    if org_id is not None:
        q = q.join(Assessment, Finding.assessment_id == Assessment.id).filter(
            Assessment.org_id == org_id
        )

    if assessment_id is not None:
        q = q.filter(Finding.assessment_id == assessment_id)
    if finding_type is not None:
        q = q.filter(Finding.finding_type == finding_type)
    if severity is not None:
        q = q.filter(Finding.severity == severity)
    if status is not None:
        q = q.filter(Finding.status == status)

    total = q.count()
    items = q.order_by(Finding.created_at.desc()).all()
    return items, total


def update_finding(db: Session, finding_id: str, **fields) -> Finding:
    """Update finding fields."""
    finding = _get_or_404(db, finding_id)

    if finding.status == "resolved":
        raise ConflictError("Cannot update a resolved finding")

    for key, value in fields.items():
        if hasattr(finding, key):
            setattr(finding, key, value)

    db.commit()
    db.refresh(finding)
    return finding


def delete_finding(db: Session, finding_id: str) -> None:
    """Delete a finding. Only open findings can be deleted."""
    finding = _get_or_404(db, finding_id)

    if finding.status != "open":
        raise ConflictError("Only open findings can be deleted")

    db.delete(finding)
    db.commit()
