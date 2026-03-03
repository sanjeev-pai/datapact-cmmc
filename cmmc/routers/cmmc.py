"""CMMC reference data API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.errors import NotFoundError
from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice
from cmmc.schemas.cmmc import (
    DomainResponse,
    LevelResponse,
    PracticeListResponse,
    PracticeResponse,
)

router = APIRouter(prefix="/api/cmmc", tags=["cmmc"])


@router.get("/domains", response_model=list[DomainResponse])
def list_domains(db: Session = Depends(get_db)):
    """Return all 14 CMMC domains."""
    return db.query(CMMCDomain).order_by(CMMCDomain.domain_id).all()


@router.get("/levels", response_model=list[LevelResponse])
def list_levels(db: Session = Depends(get_db)):
    """Return all 3 CMMC maturity levels."""
    return db.query(CMMCLevel).order_by(CMMCLevel.level).all()


@router.get("/practices", response_model=list[PracticeListResponse])
def list_practices(
    level: int | None = Query(None, ge=1, le=3),
    domain: str | None = Query(None, max_length=4),
    search: str | None = Query(None, max_length=128),
    db: Session = Depends(get_db),
):
    """Return filtered list of practices."""
    q = db.query(CMMCPractice)
    if level is not None:
        q = q.filter(CMMCPractice.level == level)
    if domain is not None:
        q = q.filter(CMMCPractice.domain_ref == domain.upper())
    if search is not None:
        pattern = f"%{search}%"
        q = q.filter(
            CMMCPractice.title.ilike(pattern) | CMMCPractice.description.ilike(pattern)
        )
    return q.order_by(CMMCPractice.practice_id).all()


@router.get("/practices/{practice_id}", response_model=PracticeResponse)
def get_practice(practice_id: str, db: Session = Depends(get_db)):
    """Return single practice detail."""
    practice = (
        db.query(CMMCPractice).filter_by(practice_id=practice_id).first()
    )
    if not practice:
        raise NotFoundError(f"Practice '{practice_id}' not found")
    return practice
