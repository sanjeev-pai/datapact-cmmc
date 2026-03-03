"""Tests for DataPact API router endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.datapact import DataPactPracticeMapping, DataPactSyncLog
from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(
    db: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    org_id: str | None = None,
    role_names: list[str] | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
        org_id=org_id,
    )
    db.add(user)
    db.flush()
    for rname in (role_names or ["viewer"]):
        role = db.query(Role).filter(Role.name == rname).first()
        if role is None:
            role = Role(name=rname)
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    return user


def _auth(user: User) -> dict:
    token = create_access_token(user.id, [r.name for r in user.roles])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_datapact(db: Session):
    """Seed org, user, domain, practices, assessment, mapping."""
    org = Organization(id="org1", name="Acme Corp")
    db.add(org)
    db.flush()

    domain = CMMCDomain(id="d_ac", domain_id="AC", name="Access Control")
    db.add(domain)

    p1 = CMMCPractice(
        id="cp1", practice_id="AC.L1-3.1.1", domain_ref="AC", level=1,
        title="Authorized Access Control",
    )
    db.add(p1)

    assessment = Assessment(
        id="a1", org_id="org1", title="Acme L1",
        target_level=1, assessment_type="self", status="in_progress",
    )
    db.add(assessment)
    db.flush()

    ap1 = AssessmentPractice(
        id="ap1", assessment_id="a1", practice_id="AC.L1-3.1.1",
        status="not_evaluated",
    )
    db.add(ap1)

    mapping = DataPactPracticeMapping(
        id="m1", org_id="org1", practice_id="AC.L1-3.1.1",
        datapact_contract_id="c1", datapact_contract_name="Alpha",
    )
    db.add(mapping)
    db.commit()

    # Users
    officer = _create_user(
        db, "officer", "officer@acme.com", org_id="org1",
        role_names=["compliance_officer"],
    )
    viewer = _create_user(
        db, "viewer", "viewer@acme.com", org_id="org1",
        role_names=["viewer"],
    )

    return {"org": org, "officer": officer, "viewer": viewer, "mapping": mapping}


# ---------------------------------------------------------------------------
# GET /contracts
# ---------------------------------------------------------------------------


MOCK_CONTRACTS = {"items": [{"id": "c1", "title": "Alpha"}], "total": 1}


def test_get_contracts_proxies(client, db, seed_datapact):
    with patch("cmmc.routers.datapact._client_for_user") as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_contracts.return_value = MOCK_CONTRACTS
        mock_factory.return_value = mock_client

        resp = client.get(
            "/api/datapact/contracts",
            headers=_auth(seed_datapact["officer"]),
        )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_contracts_requires_auth(client):
    resp = client.get("/api/datapact/contracts")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /mappings
# ---------------------------------------------------------------------------


def test_list_mappings(client, db, seed_datapact):
    resp = client.get(
        "/api/datapact/mappings",
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["practice_id"] == "AC.L1-3.1.1"


def test_list_mappings_filter_by_practice(client, db, seed_datapact):
    resp = client.get(
        "/api/datapact/mappings?practice_id=NONEXISTENT",
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /mappings
# ---------------------------------------------------------------------------


def test_create_mapping(client, db, seed_datapact):
    resp = client.post(
        "/api/datapact/mappings",
        json={
            "practice_id": "AC.L1-3.1.1",
            "datapact_contract_id": "c2",
            "datapact_contract_name": "Beta",
        },
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["datapact_contract_id"] == "c2"


def test_create_mapping_duplicate(client, db, seed_datapact):
    resp = client.post(
        "/api/datapact/mappings",
        json={"practice_id": "AC.L1-3.1.1", "datapact_contract_id": "c1"},
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 409


def test_create_mapping_viewer_forbidden(client, db, seed_datapact):
    resp = client.post(
        "/api/datapact/mappings",
        json={"practice_id": "AC.L1-3.1.1", "datapact_contract_id": "c3"},
        headers=_auth(seed_datapact["viewer"]),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /mappings/{id}
# ---------------------------------------------------------------------------


def test_delete_mapping(client, db, seed_datapact):
    mapping_id = seed_datapact["mapping"].id
    resp = client.delete(
        f"/api/datapact/mappings/{mapping_id}",
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 204


def test_delete_mapping_not_found(client, db, seed_datapact):
    resp = client.delete(
        "/api/datapact/mappings/nonexistent",
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /suggest
# ---------------------------------------------------------------------------


MOCK_CONTRACTS_SUGGEST = {
    "items": [
        {"id": "c10", "title": "Access Control Review Contract", "description": "authentication and authorization"},
        {"id": "c11", "title": "Generic Widget Contract", "description": "widget manufacturing"},
    ],
    "total": 2,
}


def test_suggest_mappings(client, db, seed_datapact):
    with patch("cmmc.routers.datapact._client_for_user") as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_contracts.return_value = MOCK_CONTRACTS_SUGGEST
        mock_factory.return_value = mock_client

        resp = client.post(
            "/api/datapact/suggest",
            headers=_auth(seed_datapact["officer"]),
        )
    assert resp.status_code == 200
    data = resp.json()
    # Should suggest AC practice ↔ c10 (access control keywords match)
    assert isinstance(data, list)
    matched_contracts = [s["contract_id"] for s in data]
    assert "c10" in matched_contracts
    # c11 ("widget manufacturing") should NOT match any domain
    assert "c11" not in matched_contracts


def test_suggest_mappings_viewer_forbidden(client, db, seed_datapact):
    resp = client.post(
        "/api/datapact/suggest",
        headers=_auth(seed_datapact["viewer"]),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /sync/{assessment_id}
# ---------------------------------------------------------------------------


COMPLIANCE = {
    "contract_id": "c1", "status": "compliant", "score": 95.0,
    "details": {"total_clauses": 10, "compliant": 9, "non_compliant": 1},
}


def test_sync_assessment(client, db, seed_datapact):
    with patch("cmmc.services.sync_service.DataPactClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get_contract_compliance.return_value = COMPLIANCE
        MockClient.return_value = mock_instance

        resp = client.post(
            "/api/datapact/sync/a1",
            headers=_auth(seed_datapact["officer"]),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "success"


def test_sync_assessment_viewer_forbidden(client, db, seed_datapact):
    resp = client.post(
        "/api/datapact/sync/a1",
        headers=_auth(seed_datapact["viewer"]),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /sync/{assessment_id}/{practice_id}
# ---------------------------------------------------------------------------


def test_sync_practice(client, db, seed_datapact):
    with patch("cmmc.services.sync_service.DataPactClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get_contract_compliance.return_value = COMPLIANCE
        MockClient.return_value = mock_instance

        resp = client.post(
            "/api/datapact/sync/a1/AC.L1-3.1.1",
            headers=_auth(seed_datapact["officer"]),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["practice_id"] == "AC.L1-3.1.1"


# ---------------------------------------------------------------------------
# GET /sync-logs
# ---------------------------------------------------------------------------


def test_sync_logs_empty(client, db, seed_datapact):
    resp = client.get(
        "/api/datapact/sync-logs",
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_sync_logs_after_sync(client, db, seed_datapact):
    """After syncing, sync-logs should return entries."""
    with patch("cmmc.services.sync_service.DataPactClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get_contract_compliance.return_value = COMPLIANCE
        MockClient.return_value = mock_instance

        client.post(
            "/api/datapact/sync/a1",
            headers=_auth(seed_datapact["officer"]),
        )

    resp = client.get(
        "/api/datapact/sync-logs",
        headers=_auth(seed_datapact["officer"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["status"] == "success"
