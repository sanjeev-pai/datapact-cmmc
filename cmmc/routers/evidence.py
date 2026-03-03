"""Evidence API endpoints — upload, list, download, delete, review."""

import os

from fastapi import APIRouter, Depends, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.errors import NotFoundError
from cmmc.models.user import User
from cmmc.schemas.evidence import (
    EvidenceListResponse,
    EvidenceResponse,
    EvidenceReview,
)
from cmmc.services import evidence_service

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

# Roles that may manage evidence (upload/delete)
_MANAGE_ROLES = ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead")

# Roles that may review evidence
_REVIEW_ROLES = ("system_admin", "org_admin", "assessor", "c3pao_lead")


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------

@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    assessment_practice_id: str = Form(...),
    title: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile | None = None,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Upload evidence with optional file attachment."""
    file_content: bytes | None = None
    file_name: str | None = None
    mime_type: str | None = None

    if file is not None and file.filename:
        file_content = await file.read()
        file_name = file.filename
        mime_type = file.content_type

    return evidence_service.upload_evidence(
        db,
        assessment_practice_id=assessment_practice_id,
        title=title,
        description=description,
        file_content=file_content,
        file_name=file_name,
        mime_type=mime_type,
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

@router.get("", response_model=EvidenceListResponse)
def list_evidence(
    assessment_practice_id: str | None = Query(None),
    assessment_id: str | None = Query(None),
    review_status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List evidence with optional filters."""
    items, total = evidence_service.list_evidence(
        db,
        assessment_practice_id=assessment_practice_id,
        assessment_id=assessment_id,
        review_status=review_status,
    )
    return EvidenceListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /{id}
# ---------------------------------------------------------------------------

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get evidence detail."""
    return evidence_service.get_evidence(db, evidence_id)


# ---------------------------------------------------------------------------
# GET /{id}/download
# ---------------------------------------------------------------------------

@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the evidence file."""
    evidence = evidence_service.get_evidence(db, evidence_id)

    if not evidence.file_path or not os.path.exists(evidence.file_path):
        raise NotFoundError("No file associated with this evidence")

    return FileResponse(
        path=evidence.file_path,
        filename=evidence.file_name or os.path.basename(evidence.file_path),
        media_type=evidence.mime_type or "application/octet-stream",
    )


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------

@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: str,
    user: User = Depends(require_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete pending evidence."""
    evidence_service.delete_evidence(db, evidence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /{id}/review
# ---------------------------------------------------------------------------

@router.post("/{evidence_id}/review", response_model=EvidenceResponse)
def review_evidence(
    evidence_id: str,
    body: EvidenceReview,
    user: User = Depends(require_role(*_REVIEW_ROLES)),
    db: Session = Depends(get_db),
):
    """Accept or reject evidence."""
    return evidence_service.review_evidence(
        db,
        evidence_id,
        reviewer_id=user.id,
        review_status=body.review_status,
    )
