"""DataPact integration API — contracts proxy, mappings, sync, sync-logs."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.models.datapact import DataPactSyncLog
from cmmc.models.user import User
from cmmc.schemas.datapact import (
    MappingCreate,
    MappingListResponse,
    MappingResponse,
    SyncLogListResponse,
    SyncLogResponse,
    SyncResultResponse,
    SyncResultsResponse,
)
from cmmc.services.datapact_client import DataPactClient
from cmmc.services.mapping_service import (
    create_mapping,
    delete_mapping,
    get_mappings,
)
from cmmc.services.sync_service import sync_assessment, sync_practice

router = APIRouter(prefix="/api/datapact", tags=["datapact"])

_WRITE_ROLES = ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead")


# ---------------------------------------------------------------------------
# GET /contracts — proxy to DataPact
# ---------------------------------------------------------------------------

@router.get("/contracts")
async def list_contracts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Proxy: list contracts from the DataPact service."""
    client = _client_for_user(db, user)
    return await client.get_contracts()


# ---------------------------------------------------------------------------
# GET /mappings
# ---------------------------------------------------------------------------

@router.get("/mappings", response_model=MappingListResponse)
def list_mappings(
    practice_id: str | None = Query(None),
    datapact_contract_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List practice-to-contract mappings for the user's org."""
    org_id = user.org_id or ""
    items = get_mappings(
        db, org_id=org_id, practice_id=practice_id,
        datapact_contract_id=datapact_contract_id,
    )
    return MappingListResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# POST /mappings
# ---------------------------------------------------------------------------

@router.post("/mappings", response_model=MappingResponse, status_code=status.HTTP_201_CREATED)
def create_mapping_endpoint(
    body: MappingCreate,
    user: User = Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    """Create a practice-to-contract mapping."""
    org_id = user.org_id or ""
    return create_mapping(
        db,
        org_id=org_id,
        practice_id=body.practice_id,
        datapact_contract_id=body.datapact_contract_id,
        datapact_contract_name=body.datapact_contract_name,
    )


# ---------------------------------------------------------------------------
# DELETE /mappings/{id}
# ---------------------------------------------------------------------------

@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping_endpoint(
    mapping_id: str,
    user: User = Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete a practice-to-contract mapping."""
    delete_mapping(db, mapping_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /sync/{assessment_id}
# ---------------------------------------------------------------------------

@router.post("/sync/{assessment_id}", response_model=SyncResultsResponse)
async def sync_assessment_endpoint(
    assessment_id: str,
    user: User = Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    """Trigger a full sync for all mapped practices in an assessment."""
    results = await sync_assessment(db, assessment_id)
    return SyncResultsResponse(results=results)


# ---------------------------------------------------------------------------
# POST /sync/{assessment_id}/{practice_id}
# ---------------------------------------------------------------------------

@router.post("/sync/{assessment_id}/{practice_id}", response_model=SyncResultResponse)
async def sync_practice_endpoint(
    assessment_id: str,
    practice_id: str,
    user: User = Depends(require_role(*_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    """Sync a single practice with DataPact."""
    result = await sync_practice(db, assessment_id, practice_id)
    return SyncResultResponse(**result)


# ---------------------------------------------------------------------------
# GET /sync-logs
# ---------------------------------------------------------------------------

@router.get("/sync-logs", response_model=SyncLogListResponse)
def list_sync_logs(
    assessment_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent sync log entries."""
    org_id = user.org_id or ""
    query = db.query(DataPactSyncLog).filter_by(org_id=org_id)
    if assessment_id:
        query = query.filter_by(assessment_id=assessment_id)
    query = query.order_by(DataPactSyncLog.created_at.desc()).limit(limit)
    items = query.all()
    return SyncLogListResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_for_user(db: Session, user: User) -> DataPactClient:
    """Build a DataPactClient from the user's org settings."""
    from cmmc.models.organization import Organization

    kwargs: dict = {}
    if user.org_id:
        org = db.query(Organization).filter_by(id=user.org_id).first()
        if org:
            if org.datapact_api_url:
                kwargs["base_url"] = org.datapact_api_url
            if org.datapact_api_key:
                kwargs["api_key"] = org.datapact_api_key
    return DataPactClient(**kwargs)
