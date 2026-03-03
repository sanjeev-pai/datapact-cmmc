"""Practice-to-contract mapping service for DataPact integration."""

from __future__ import annotations

from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.cmmc_ref import CMMCPractice
from cmmc.models.datapact import DataPactPracticeMapping
from cmmc.models.organization import Organization

# Keywords per domain used for auto-suggest matching
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "AC": ["access control", "access management", "authentication", "authorization", "user access", "login", "identity"],
    "AT": ["awareness", "training", "security training", "education"],
    "AU": ["audit", "logging", "accountability", "audit trail", "log management"],
    "CA": ["security assessment", "assessment", "authorization", "compliance assessment"],
    "CM": ["configuration", "configuration management", "baseline", "change control"],
    "IA": ["identification", "authentication", "identity", "credentials", "multi-factor", "mfa", "password"],
    "IR": ["incident", "incident response", "breach", "security incident"],
    "MA": ["maintenance", "system maintenance", "patching"],
    "MP": ["media", "media protection", "removable media", "data disposal"],
    "PE": ["physical", "physical access", "physical security", "facility"],
    "PS": ["personnel", "personnel security", "background check", "screening"],
    "RA": ["risk", "risk assessment", "vulnerability", "threat assessment"],
    "SC": ["system", "communications", "boundary", "firewall", "encryption", "network", "communications protection"],
    "SI": ["system integrity", "integrity", "monitoring", "malware", "flaw remediation", "antivirus"],
}


def create_mapping(
    db: Session,
    *,
    org_id: str,
    practice_id: str,
    datapact_contract_id: str,
    datapact_contract_name: str | None = None,
) -> DataPactPracticeMapping:
    """Create a mapping between a CMMC practice and a DataPact contract.

    Raises NotFoundError if org or practice doesn't exist.
    Raises ConflictError if the exact mapping already exists.
    """
    # Validate org
    org = db.query(Organization).filter_by(id=org_id).first()
    if not org:
        raise NotFoundError(f"Organization {org_id} not found")

    # Validate practice
    practice = db.query(CMMCPractice).filter_by(practice_id=practice_id).first()
    if not practice:
        raise NotFoundError(f"Practice {practice_id} not found")

    # Check duplicate
    existing = (
        db.query(DataPactPracticeMapping)
        .filter_by(
            org_id=org_id,
            practice_id=practice_id,
            datapact_contract_id=datapact_contract_id,
        )
        .first()
    )
    if existing:
        raise ConflictError(
            f"Mapping already exists: {practice_id} ↔ {datapact_contract_id}"
        )

    mapping = DataPactPracticeMapping(
        org_id=org_id,
        practice_id=practice_id,
        datapact_contract_id=datapact_contract_id,
        datapact_contract_name=datapact_contract_name,
    )
    db.add(mapping)
    db.flush()
    db.commit()
    return mapping


def get_mappings(
    db: Session,
    *,
    org_id: str,
    practice_id: str | None = None,
    datapact_contract_id: str | None = None,
) -> list[DataPactPracticeMapping]:
    """List mappings for an org, optionally filtered by practice or contract."""
    query = db.query(DataPactPracticeMapping).filter_by(org_id=org_id)

    if practice_id:
        query = query.filter_by(practice_id=practice_id)
    if datapact_contract_id:
        query = query.filter_by(datapact_contract_id=datapact_contract_id)

    return query.order_by(DataPactPracticeMapping.practice_id).all()


def delete_mapping(db: Session, mapping_id: str) -> None:
    """Delete a mapping by ID. Raises NotFoundError if not found."""
    mapping = db.query(DataPactPracticeMapping).filter_by(id=mapping_id).first()
    if not mapping:
        raise NotFoundError(f"Mapping {mapping_id} not found")
    db.delete(mapping)
    db.flush()
    db.commit()


def suggest_mappings(
    db: Session,
    *,
    org_id: str,
    contracts: list[dict],
) -> list[dict]:
    """Auto-suggest practice-to-contract mappings based on domain keyword matching.

    Parameters
    ----------
    contracts : list[dict]
        Contracts from DataPact API, each with ``id``, ``title``, ``description``.

    Returns
    -------
    list[dict]
        Suggestions: ``[{practice_id, contract_id, contract_name, reason}]``.
        Excludes pairs that already exist as mappings for the org.
    """
    # Load all practices with their domain
    practices = db.query(CMMCPractice).all()
    if not practices:
        return []

    # Load existing mappings to exclude
    existing = db.query(DataPactPracticeMapping).filter_by(org_id=org_id).all()
    existing_pairs = {(m.practice_id, m.datapact_contract_id) for m in existing}

    suggestions: list[dict] = []

    for contract in contracts:
        contract_id = contract.get("id", "")
        contract_title = contract.get("title", "")
        contract_desc = contract.get("description", "")
        contract_text = f"{contract_title} {contract_desc}".lower()

        for practice in practices:
            # Skip if already mapped
            if (practice.practice_id, contract_id) in existing_pairs:
                continue

            domain_id = practice.domain_ref
            keywords = _DOMAIN_KEYWORDS.get(domain_id, [])

            matched_keywords = [kw for kw in keywords if kw in contract_text]
            if matched_keywords:
                suggestions.append(
                    {
                        "practice_id": practice.practice_id,
                        "contract_id": contract_id,
                        "contract_name": contract_title,
                        "reason": f"Domain {domain_id} keywords matched: {', '.join(matched_keywords[:3])}",
                    }
                )

    return suggestions
