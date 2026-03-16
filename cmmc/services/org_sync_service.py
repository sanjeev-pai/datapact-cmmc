"""Organization-to-DataPact tenant synchronization service."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.organization import Organization
from cmmc.services.datapact_client import DataPactClient, DataPactError

logger = logging.getLogger(__name__)


async def create_org_with_datapact(
    db: Session,
    *,
    name: str,
    cage_code: str | None = None,
    duns_number: str | None = None,
    target_level: int | None = None,
    creator_id: str = "system",
    client: DataPactClient | None = None,
) -> Organization:
    """Create an organization locally and as a DataPact tenant.

    Creates the tenant in DataPact first; if that succeeds, stores the
    ``datapact_tenant_id`` on the local Organization row.
    """
    if db.query(Organization).filter(Organization.name == name).first():
        raise ConflictError("Organization name already exists")

    tenant_id: str | None = None
    if client is not None:
        try:
            tenant_data = await client.create_tenant(
                {"name": name, "slug": _slugify(name), "owner_email": f"admin@{_slugify(name)}.local"}
            )
            tenant_id = tenant_data.get("id")
        except DataPactError:
            logger.warning("Failed to create DataPact tenant for %s, continuing without", name)

    org = Organization(
        name=name,
        cage_code=cage_code,
        duns_number=duns_number,
        target_level=target_level,
        datapact_tenant_id=tenant_id,
        creator_id=creator_id,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


async def sync_org_from_datapact(
    db: Session,
    org_id: str,
    *,
    client: DataPactClient,
) -> Organization:
    """Pull tenant data from DataPact and update the local organization."""
    org = db.query(Organization).filter_by(id=org_id).first()
    if not org:
        raise NotFoundError("Organization not found")

    if not org.datapact_tenant_id:
        raise ConflictError("Organization has no linked DataPact tenant")

    tenant = await client.get_tenant(org.datapact_tenant_id)

    # Update local fields from DataPact tenant data
    if tenant.get("name"):
        org.name = tenant["name"]

    db.commit()
    db.refresh(org)
    return org


async def update_org_with_datapact(
    db: Session,
    org_id: str,
    updates: dict[str, Any],
    *,
    client: DataPactClient | None = None,
) -> Organization:
    """Update an organization locally and push changes to DataPact."""
    org = db.query(Organization).filter_by(id=org_id).first()
    if not org:
        raise NotFoundError("Organization not found")

    # Push to DataPact if linked
    if client is not None and org.datapact_tenant_id:
        tenant_updates: dict[str, Any] = {}
        if "name" in updates:
            tenant_updates["name"] = updates["name"]
        if tenant_updates:
            try:
                await client.update_tenant(org.datapact_tenant_id, tenant_updates)
            except DataPactError:
                logger.warning("Failed to update DataPact tenant %s", org.datapact_tenant_id)

    # Apply local updates
    for key, value in updates.items():
        if hasattr(org, key) and value is not None:
            setattr(org, key, value)

    db.commit()
    db.refresh(org)
    return org


async def link_org_to_tenant(
    db: Session,
    org_id: str,
    tenant_id: str,
    *,
    client: DataPactClient,
) -> Organization:
    """Link an existing organization to an existing DataPact tenant."""
    org = db.query(Organization).filter_by(id=org_id).first()
    if not org:
        raise NotFoundError("Organization not found")

    # Verify tenant exists
    await client.get_tenant(tenant_id)

    org.datapact_tenant_id = tenant_id
    db.commit()
    db.refresh(org)
    return org


def _slugify(name: str) -> str:
    """Simple slug generation from name."""
    return name.lower().replace(" ", "-").replace("_", "-")[:128]
