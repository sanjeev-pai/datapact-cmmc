"""POA&M business logic — CRUD, item management, auto-generation from findings."""

from datetime import date

from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.finding import Finding
from cmmc.models.poam import POAM, POAMItem

# Valid status transitions
_POAM_TRANSITIONS = {
    "draft": {"active"},
    "active": {"completed"},
    "completed": set(),
}

_ITEM_TRANSITIONS = {
    "open": {"in_progress"},
    "in_progress": {"completed"},
    "completed": set(),
}


# ---------------------------------------------------------------------------
# POA&M CRUD
# ---------------------------------------------------------------------------


def create_poam(
    db: Session,
    *,
    org_id: str,
    title: str,
    assessment_id: str | None = None,
) -> POAM:
    """Create a new POA&M in draft status."""
    poam = POAM(
        org_id=org_id,
        title=title,
        assessment_id=assessment_id,
        status="draft",
    )
    db.add(poam)
    db.flush()
    db.commit()
    return poam


def get_poam(db: Session, poam_id: str) -> POAM:
    """Get a POA&M by ID. Raises NotFoundError if not found."""
    poam = db.query(POAM).filter_by(id=poam_id).first()
    if not poam:
        raise NotFoundError(f"POA&M {poam_id} not found")
    return poam


def list_poams(
    db: Session,
    *,
    org_id: str | None = None,
    assessment_id: str | None = None,
    status: str | None = None,
) -> tuple[list[POAM], int]:
    """List POA&Ms with optional filters. Returns (items, total)."""
    query = db.query(POAM)
    if org_id:
        query = query.filter_by(org_id=org_id)
    if assessment_id:
        query = query.filter_by(assessment_id=assessment_id)
    if status:
        query = query.filter_by(status=status)

    query = query.order_by(POAM.created_at.desc())
    items = query.all()
    return items, len(items)


def update_poam(
    db: Session,
    poam_id: str,
    **kwargs: str | None,
) -> POAM:
    """Update POA&M fields. Raises ConflictError if completed."""
    poam = get_poam(db, poam_id)

    if poam.status == "completed":
        raise ConflictError("Cannot update a completed POA&M")

    for key, value in kwargs.items():
        if value is not None and hasattr(poam, key):
            setattr(poam, key, value)

    db.flush()
    db.commit()
    return poam


def delete_poam(db: Session, poam_id: str) -> None:
    """Delete a draft POA&M. Raises ConflictError if not draft."""
    poam = get_poam(db, poam_id)

    if poam.status != "draft":
        raise ConflictError("Only draft POA&Ms can be deleted")

    db.query(POAMItem).filter_by(poam_id=poam_id).delete()
    db.delete(poam)
    db.flush()
    db.commit()


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def activate_poam(db: Session, poam_id: str) -> POAM:
    """Transition draft -> active."""
    return _transition_poam(db, poam_id, "active")


def complete_poam(db: Session, poam_id: str) -> POAM:
    """Transition active -> completed."""
    return _transition_poam(db, poam_id, "completed")


def _transition_poam(db: Session, poam_id: str, target_status: str) -> POAM:
    """Transition POA&M to a new status."""
    poam = get_poam(db, poam_id)
    allowed = _POAM_TRANSITIONS.get(poam.status, set())

    if target_status not in allowed:
        raise ConflictError(
            f"Cannot transition POA&M from '{poam.status}' to '{target_status}'"
        )

    poam.status = target_status
    db.flush()
    db.commit()
    return poam


# ---------------------------------------------------------------------------
# POA&M Item CRUD
# ---------------------------------------------------------------------------


def add_item(
    db: Session,
    poam_id: str,
    *,
    finding_id: str | None = None,
    practice_id: str | None = None,
    milestone: str | None = None,
    scheduled_completion: date | None = None,
    resources_required: str | None = None,
    risk_accepted: bool = False,
) -> POAMItem:
    """Add an item to a POA&M."""
    poam = get_poam(db, poam_id)
    if poam.status == "completed":
        raise ConflictError("Cannot add items to a completed POA&M")

    item = POAMItem(
        poam_id=poam_id,
        finding_id=finding_id,
        practice_id=practice_id,
        milestone=milestone,
        scheduled_completion=scheduled_completion,
        resources_required=resources_required,
        risk_accepted=risk_accepted,
        status="open",
    )
    db.add(item)
    db.flush()
    db.commit()
    return item


def get_item(db: Session, item_id: str) -> POAMItem:
    """Get a POA&M item by ID."""
    item = db.query(POAMItem).filter_by(id=item_id).first()
    if not item:
        raise NotFoundError(f"POA&M item {item_id} not found")
    return item


def update_item(
    db: Session,
    item_id: str,
    **kwargs: str | date | bool | None,
) -> POAMItem:
    """Update a POA&M item."""
    item = get_item(db, item_id)

    # Check parent POAM is not completed
    poam = get_poam(db, item.poam_id)
    if poam.status == "completed":
        raise ConflictError("Cannot update items on a completed POA&M")

    # Handle status transition if requested
    new_status = kwargs.pop("status", None)
    if new_status is not None:
        allowed = _ITEM_TRANSITIONS.get(item.status, set())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot transition item from '{item.status}' to '{new_status}'"
            )
        item.status = new_status

    for key, value in kwargs.items():
        if value is not None and hasattr(item, key):
            setattr(item, key, value)

    db.flush()
    db.commit()
    return item


def remove_item(db: Session, item_id: str) -> None:
    """Remove a POA&M item."""
    item = get_item(db, item_id)

    poam = get_poam(db, item.poam_id)
    if poam.status == "completed":
        raise ConflictError("Cannot remove items from a completed POA&M")

    db.delete(item)
    db.flush()
    db.commit()


# ---------------------------------------------------------------------------
# Auto-generation
# ---------------------------------------------------------------------------


def generate_from_assessment(
    db: Session,
    poam_id: str,
    assessment_id: str,
) -> list[POAMItem]:
    """Auto-generate POA&M items from unresolved findings for an assessment.

    Creates one POA&M item per finding with status 'open'.
    Returns list of created items.
    """
    poam = get_poam(db, poam_id)
    if poam.status == "completed":
        raise ConflictError("Cannot generate items for a completed POA&M")

    findings = (
        db.query(Finding)
        .filter_by(assessment_id=assessment_id, status="open")
        .all()
    )

    created: list[POAMItem] = []
    for finding in findings:
        item = POAMItem(
            poam_id=poam_id,
            finding_id=finding.id,
            practice_id=finding.practice_id,
            milestone=finding.title,
            status="open",
        )
        db.add(item)
        created.append(item)

    db.flush()
    db.commit()
    return created


# ---------------------------------------------------------------------------
# Overdue detection
# ---------------------------------------------------------------------------


def get_overdue_items(db: Session, poam_id: str) -> list[POAMItem]:
    """Return items past their scheduled_completion that are not completed."""
    today = date.today()
    return (
        db.query(POAMItem)
        .filter(
            POAMItem.poam_id == poam_id,
            POAMItem.status != "completed",
            POAMItem.scheduled_completion.isnot(None),
            POAMItem.scheduled_completion < today,
        )
        .all()
    )
