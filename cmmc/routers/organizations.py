"""Organization CRUD API endpoints with DataPact tenant delegation."""

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user, require_role
from cmmc.errors import ConflictError, ForbiddenError, NotFoundError
from cmmc.models.organization import Organization
from cmmc.models.user import User
from cmmc.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from cmmc.services.datapact_client import DataPactClient, DataPactError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def _build_client_for_org(org: Organization | None = None) -> DataPactClient | None:
    """Build a DataPactClient from org settings if available."""
    try:
        kwargs: dict = {}
        if org and org.datapact_api_url:
            kwargs["base_url"] = org.datapact_api_url
        if org and org.datapact_api_key:
            kwargs["api_key"] = org.datapact_api_key
        return DataPactClient(**kwargs)
    except Exception:
        return None


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    user: User = Depends(require_role("system_admin")),
    db: Session = Depends(get_db),
):
    """Create a new organization. System admin only.

    If DataPact is available, also creates a corresponding tenant.
    """
    if db.query(Organization).filter(Organization.name == body.name).first():
        raise ConflictError("Organization name already exists")

    # Try to create a DataPact tenant
    tenant_id: str | None = None
    client = _build_client_for_org()
    if client:
        try:
            slug = body.name.lower().replace(" ", "-").replace("_", "-")[:128]
            tenant_data = await client.create_tenant(
                {"name": body.name, "slug": slug, "owner_email": f"admin@{slug}.local"}
            )
            tenant_id = tenant_data.get("id")
        except DataPactError:
            logger.warning("Failed to create DataPact tenant for %s", body.name)

    org = Organization(
        name=body.name,
        cage_code=body.cage_code,
        duns_number=body.duns_number,
        target_level=body.target_level,
        datapact_tenant_id=tenant_id,
        creator_id=user.id,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List organizations. System admin sees all; others see only their own org."""
    user_roles = {r.name for r in user.roles}
    if "system_admin" in user_roles:
        return db.query(Organization).order_by(Organization.name).all()

    if user.org_id:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        return [org] if org else []
    return []


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get organization detail, enriched with DataPact tenant data if linked."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization not found")

    user_roles = {r.name for r in user.roles}
    if "system_admin" not in user_roles and user.org_id != org.id:
        raise ForbiddenError("Access denied to this organization")

    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update organization. Pushes name changes to DataPact if linked."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization not found")

    user_roles = {r.name for r in user.roles}
    is_system_admin = "system_admin" in user_roles
    is_own_org_admin = "org_admin" in user_roles and user.org_id == org.id

    if not is_system_admin and not is_own_org_admin:
        raise ForbiddenError("Insufficient permissions")

    if body.name is not None and body.name != org.name:
        if db.query(Organization).filter(Organization.name == body.name, Organization.id != org.id).first():
            raise ConflictError("Organization name already exists")
        # Push name change to DataPact if linked
        if org.datapact_tenant_id:
            client = _build_client_for_org(org)
            if client:
                try:
                    await client.update_tenant(org.datapact_tenant_id, {"name": body.name})
                except DataPactError:
                    logger.warning("Failed to update DataPact tenant %s", org.datapact_tenant_id)
        org.name = body.name

    if body.cage_code is not None:
        org.cage_code = body.cage_code
    if body.duns_number is not None:
        org.duns_number = body.duns_number
    if body.target_level is not None:
        org.target_level = body.target_level
    if body.datapact_api_url is not None:
        org.datapact_api_url = body.datapact_api_url
    if body.datapact_api_key is not None:
        org.datapact_api_key = body.datapact_api_key

    db.commit()
    db.refresh(org)
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: str,
    user: User = Depends(require_role("system_admin")),
    db: Session = Depends(get_db),
):
    """Delete organization. System admin only."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise NotFoundError("Organization not found")

    db.delete(org)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
