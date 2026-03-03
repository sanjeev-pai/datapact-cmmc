"""Tests for practice-to-contract mapping service."""

import pytest
from sqlalchemy.orm import Session

from cmmc.errors import ConflictError, NotFoundError
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.datapact import DataPactPracticeMapping
from cmmc.models.organization import Organization
from cmmc.services.mapping_service import (
    create_mapping,
    delete_mapping,
    get_mappings,
    suggest_mappings,
)


@pytest.fixture
def seed_data(db: Session):
    """Seed an org, domain, and practices for mapping tests."""
    org = Organization(id="org1", name="Acme Corp")
    db.add(org)

    domain_ac = CMMCDomain(id="d_ac", domain_id="AC", name="Access Control", description="Manage access")
    domain_sc = CMMCDomain(id="d_sc", domain_id="SC", name="System and Communications Protection", description="Protect communications")
    db.add_all([domain_ac, domain_sc])

    p1 = CMMCPractice(
        id="p1", practice_id="AC.L1-3.1.1", domain_ref="AC", level=1,
        title="Authorized Access Control", description="Limit system access to authorized users.",
    )
    p2 = CMMCPractice(
        id="p2", practice_id="SC.L1-3.13.1", domain_ref="SC", level=1,
        title="Boundary Protection", description="Monitor and control communications at system boundaries.",
    )
    db.add_all([p1, p2])
    db.commit()
    return {"org": org, "practices": [p1, p2], "domains": [domain_ac, domain_sc]}


# ── create_mapping ───────────────────────────────────────────────────────────


def test_create_mapping_success(db: Session, seed_data):
    mapping = create_mapping(
        db,
        org_id="org1",
        practice_id="AC.L1-3.1.1",
        datapact_contract_id="contract-abc",
        datapact_contract_name="DoD Alpha Contract",
    )
    assert mapping.id is not None
    assert mapping.org_id == "org1"
    assert mapping.practice_id == "AC.L1-3.1.1"
    assert mapping.datapact_contract_id == "contract-abc"
    assert mapping.datapact_contract_name == "DoD Alpha Contract"


def test_create_mapping_without_contract_name(db: Session, seed_data):
    mapping = create_mapping(
        db,
        org_id="org1",
        practice_id="AC.L1-3.1.1",
        datapact_contract_id="contract-xyz",
    )
    assert mapping.datapact_contract_name is None


def test_create_mapping_invalid_org(db: Session, seed_data):
    with pytest.raises(NotFoundError, match="Organization"):
        create_mapping(
            db,
            org_id="nonexistent",
            practice_id="AC.L1-3.1.1",
            datapact_contract_id="contract-abc",
        )


def test_create_mapping_invalid_practice(db: Session, seed_data):
    with pytest.raises(NotFoundError, match="Practice"):
        create_mapping(
            db,
            org_id="org1",
            practice_id="XX.L1-9.9.9",
            datapact_contract_id="contract-abc",
        )


def test_create_mapping_duplicate(db: Session, seed_data):
    create_mapping(
        db,
        org_id="org1",
        practice_id="AC.L1-3.1.1",
        datapact_contract_id="contract-abc",
    )
    with pytest.raises(ConflictError, match="already exists"):
        create_mapping(
            db,
            org_id="org1",
            practice_id="AC.L1-3.1.1",
            datapact_contract_id="contract-abc",
        )


def test_create_mapping_same_practice_different_contract(db: Session, seed_data):
    """A practice can map to multiple contracts."""
    m1 = create_mapping(db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c1")
    m2 = create_mapping(db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c2")
    assert m1.id != m2.id


# ── get_mappings ─────────────────────────────────────────────────────────────


def test_get_mappings_by_org(db: Session, seed_data):
    create_mapping(db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c1")
    create_mapping(db, org_id="org1", practice_id="SC.L1-3.13.1", datapact_contract_id="c2")
    result = get_mappings(db, org_id="org1")
    assert len(result) == 2


def test_get_mappings_filter_by_practice(db: Session, seed_data):
    create_mapping(db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c1")
    create_mapping(db, org_id="org1", practice_id="SC.L1-3.13.1", datapact_contract_id="c2")
    result = get_mappings(db, org_id="org1", practice_id="AC.L1-3.1.1")
    assert len(result) == 1
    assert result[0].practice_id == "AC.L1-3.1.1"


def test_get_mappings_filter_by_contract(db: Session, seed_data):
    create_mapping(db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c1")
    create_mapping(db, org_id="org1", practice_id="SC.L1-3.13.1", datapact_contract_id="c2")
    result = get_mappings(db, org_id="org1", datapact_contract_id="c2")
    assert len(result) == 1
    assert result[0].datapact_contract_id == "c2"


def test_get_mappings_empty(db: Session, seed_data):
    result = get_mappings(db, org_id="org1")
    assert result == []


# ── delete_mapping ───────────────────────────────────────────────────────────


def test_delete_mapping_success(db: Session, seed_data):
    mapping = create_mapping(
        db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c1"
    )
    delete_mapping(db, mapping.id)
    result = get_mappings(db, org_id="org1")
    assert len(result) == 0


def test_delete_mapping_not_found(db: Session, seed_data):
    with pytest.raises(NotFoundError, match="Mapping"):
        delete_mapping(db, "nonexistent-id")


# ── suggest_mappings ─────────────────────────────────────────────────────────


def test_suggest_mappings_matches_domain_keywords(db: Session, seed_data):
    contracts = [
        {
            "id": "c1",
            "title": "Access Control System Contract",
            "description": "Manage user access and authentication systems.",
        },
        {
            "id": "c2",
            "title": "Network Boundary Protection",
            "description": "Firewall and communications protection services.",
        },
        {
            "id": "c3",
            "title": "Office Supply Procurement",
            "description": "General office supplies and furniture.",
        },
    ]
    suggestions = suggest_mappings(db, org_id="org1", contracts=contracts)
    # Should suggest matches — AC practices to c1, SC practices to c2
    assert len(suggestions) > 0
    practice_ids = {s["practice_id"] for s in suggestions}
    contract_ids = {s["contract_id"] for s in suggestions}
    # AC practice should match the access control contract
    assert "AC.L1-3.1.1" in practice_ids
    assert "c1" in contract_ids


def test_suggest_mappings_excludes_existing(db: Session, seed_data):
    """Already-mapped pairs should not be re-suggested."""
    create_mapping(
        db, org_id="org1", practice_id="AC.L1-3.1.1", datapact_contract_id="c1"
    )
    contracts = [
        {"id": "c1", "title": "Access Control System", "description": "Access management."},
    ]
    suggestions = suggest_mappings(db, org_id="org1", contracts=contracts)
    # AC.L1-3.1.1 ↔ c1 already exists, should not be suggested
    for s in suggestions:
        assert not (s["practice_id"] == "AC.L1-3.1.1" and s["contract_id"] == "c1")


def test_suggest_mappings_no_matches(db: Session, seed_data):
    contracts = [
        {"id": "c99", "title": "Catering Services", "description": "Food and beverage."},
    ]
    suggestions = suggest_mappings(db, org_id="org1", contracts=contracts)
    assert suggestions == []
