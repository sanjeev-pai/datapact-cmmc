"""Tests for DataPact API client."""

import httpx
import pytest
import respx

from cmmc.services.datapact_client import (
    DataPactAuthError,
    DataPactClient,
    DataPactConnectionError,
    DataPactError,
    DataPactNotFoundError,
    DataPactRateLimitError,
)

BASE_URL = "http://datapact.test:8000"
API_KEY = "test-api-key-123"


@pytest.fixture
def client():
    return DataPactClient(base_url=BASE_URL, api_key=API_KEY, timeout=5)


SAMPLE_CONTRACTS = {
    "items": [
        {
            "id": "c1",
            "title": "DoD Contract Alpha",
            "description": "Defense contract for cyber services",
            "status": "active",
            "parties": ["DoD", "Acme Corp"],
            "created_at": "2025-06-01T00:00:00Z",
            "updated_at": "2025-12-01T00:00:00Z",
        },
        {
            "id": "c2",
            "title": "Navy Supply Chain",
            "description": "Supply chain management contract",
            "status": "active",
            "parties": ["Navy", "Acme Corp"],
            "created_at": "2025-08-15T00:00:00Z",
            "updated_at": "2026-01-10T00:00:00Z",
        },
    ],
    "total": 2,
}

SAMPLE_CONTRACT = SAMPLE_CONTRACTS["items"][0]

SAMPLE_COMPLIANCE = {
    "contract_id": "c1",
    "status": "partially_compliant",
    "score": 78.5,
    "details": {
        "total_clauses": 42,
        "compliant": 33,
        "non_compliant": 5,
        "pending_review": 4,
    },
}


# ── get_contracts ────────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_get_contracts_success(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_CONTRACTS)
    )
    result = await client.get_contracts()
    assert result == SAMPLE_CONTRACTS
    assert len(result["items"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_contracts_normalizes_results_key(client):
    """DataPact returns 'results' — client should normalize to 'items'."""
    datapact_response = {"results": SAMPLE_CONTRACTS["items"], "total": 2}
    respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(200, json=datapact_response)
    )
    result = await client.get_contracts()
    assert "items" in result
    assert "results" not in result
    assert len(result["items"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_contracts_sends_auth_header(client):
    route = respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_CONTRACTS)
    )
    await client.get_contracts()
    assert route.called
    request = route.calls[0].request
    assert request.headers["authorization"] == f"Bearer {API_KEY}"


@respx.mock
@pytest.mark.asyncio
async def test_get_contracts_no_api_key():
    client = DataPactClient(base_url=BASE_URL, api_key=None, timeout=5)
    route = respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(200, json=SAMPLE_CONTRACTS)
    )
    await client.get_contracts()
    assert route.called
    request = route.calls[0].request
    assert "authorization" not in request.headers


# ── get_contract ─────────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_get_contract_success(client):
    respx.get(f"{BASE_URL}/api/contracts/c1").mock(
        return_value=httpx.Response(200, json=SAMPLE_CONTRACT)
    )
    result = await client.get_contract("c1")
    assert result["id"] == "c1"
    assert result["title"] == "DoD Contract Alpha"


@respx.mock
@pytest.mark.asyncio
async def test_get_contract_not_found(client):
    respx.get(f"{BASE_URL}/api/contracts/missing").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(DataPactNotFoundError, match="missing"):
        await client.get_contract("missing")


# ── get_contract_compliance ──────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_get_contract_compliance_success(client):
    respx.get(f"{BASE_URL}/api/contracts/c1/compliance").mock(
        return_value=httpx.Response(200, json=SAMPLE_COMPLIANCE)
    )
    result = await client.get_contract_compliance("c1")
    assert result["contract_id"] == "c1"
    assert result["score"] == 78.5


@respx.mock
@pytest.mark.asyncio
async def test_get_contract_compliance_not_found(client):
    respx.get(f"{BASE_URL}/api/contracts/bad/compliance").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(DataPactNotFoundError):
        await client.get_contract_compliance("bad")


# ── Tenant methods ───────────────────────────────────────────────────────────


SAMPLE_TENANT = {
    "id": "t1",
    "name": "Acme Defense Corp",
    "slug": "acme-defense",
    "plan": "pro",
    "status": "active",
    "owner_email": "admin@acme.com",
}

SAMPLE_TENANTS = {"results": [SAMPLE_TENANT], "total": 1}


@respx.mock
@pytest.mark.asyncio
async def test_get_tenants_success(client):
    respx.get(f"{BASE_URL}/api/tenants").mock(
        return_value=httpx.Response(200, json=SAMPLE_TENANTS)
    )
    result = await client.get_tenants()
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "Acme Defense Corp"


@respx.mock
@pytest.mark.asyncio
async def test_get_tenant_success(client):
    respx.get(f"{BASE_URL}/api/tenants/t1").mock(
        return_value=httpx.Response(200, json=SAMPLE_TENANT)
    )
    result = await client.get_tenant("t1")
    assert result["id"] == "t1"
    assert result["name"] == "Acme Defense Corp"


@respx.mock
@pytest.mark.asyncio
async def test_get_tenant_not_found(client):
    respx.get(f"{BASE_URL}/api/tenants/missing").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(DataPactNotFoundError):
        await client.get_tenant("missing")


@respx.mock
@pytest.mark.asyncio
async def test_create_tenant_success(client):
    new_tenant = {"name": "New Corp", "slug": "new-corp", "owner_email": "a@b.com"}
    created = {**new_tenant, "id": "t2", "plan": "free", "status": "active"}
    route = respx.post(f"{BASE_URL}/api/tenants").mock(
        return_value=httpx.Response(201, json=created)
    )
    result = await client.create_tenant(new_tenant)
    assert result["id"] == "t2"
    assert route.called
    # Verify POST body
    request = route.calls[0].request
    assert request.headers["authorization"] == f"Bearer {API_KEY}"


@respx.mock
@pytest.mark.asyncio
async def test_update_tenant_success(client):
    updated = {**SAMPLE_TENANT, "name": "Acme Updated"}
    route = respx.put(f"{BASE_URL}/api/tenants/t1").mock(
        return_value=httpx.Response(200, json=updated)
    )
    result = await client.update_tenant("t1", {"name": "Acme Updated"})
    assert result["name"] == "Acme Updated"
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_delete_tenant_success(client):
    route = respx.delete(f"{BASE_URL}/api/tenants/t1").mock(
        return_value=httpx.Response(204)
    )
    await client.delete_tenant("t1")
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_delete_tenant_not_found(client):
    respx.delete(f"{BASE_URL}/api/tenants/missing").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(DataPactNotFoundError):
        await client.delete_tenant("missing")


# ── Compliance Scoring methods ───────────────────────────────────────────────

SAMPLE_SCORES = {
    "results": [
        {"contract_id": "c1", "score": 85.0, "status": "compliant"},
        {"contract_id": "c2", "score": 60.0, "status": "partially_compliant"},
    ],
    "total": 2,
}

SAMPLE_ORG_SCORE = {
    "overall_score": 72.5,
    "total_contracts": 5,
    "compliant": 3,
    "non_compliant": 2,
}


@respx.mock
@pytest.mark.asyncio
async def test_get_compliance_scores_success(client):
    respx.get(f"{BASE_URL}/api/compliance/scores").mock(
        return_value=httpx.Response(200, json=SAMPLE_SCORES)
    )
    result = await client.get_compliance_scores()
    assert "items" in result
    assert len(result["items"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_compliance_score_success(client):
    score = {"contract_id": "c1", "score": 85.0, "status": "compliant"}
    respx.get(f"{BASE_URL}/api/compliance/scores/c1").mock(
        return_value=httpx.Response(200, json=score)
    )
    result = await client.get_compliance_score("c1")
    assert result["score"] == 85.0


@respx.mock
@pytest.mark.asyncio
async def test_get_org_compliance_score_success(client):
    respx.get(f"{BASE_URL}/api/compliance/scores/org").mock(
        return_value=httpx.Response(200, json=SAMPLE_ORG_SCORE)
    )
    result = await client.get_org_compliance_score()
    assert result["overall_score"] == 72.5
    assert result["total_contracts"] == 5


# ── Certification methods ────────────────────────────────────────────────────

SAMPLE_CERTIFICATIONS = {
    "results": [
        {"contract_id": "c1", "tier": "gold", "status": "certified"},
    ],
    "total": 1,
}


@respx.mock
@pytest.mark.asyncio
async def test_get_certifications_success(client):
    respx.get(f"{BASE_URL}/api/certifications").mock(
        return_value=httpx.Response(200, json=SAMPLE_CERTIFICATIONS)
    )
    result = await client.get_certifications()
    assert "items" in result
    assert result["items"][0]["tier"] == "gold"


@respx.mock
@pytest.mark.asyncio
async def test_get_certification_success(client):
    cert = {"contract_id": "c1", "tier": "gold", "status": "certified"}
    respx.get(f"{BASE_URL}/api/certifications/c1").mock(
        return_value=httpx.Response(200, json=cert)
    )
    result = await client.get_certification("c1")
    assert result["tier"] == "gold"


@respx.mock
@pytest.mark.asyncio
async def test_evaluate_certifications_success(client):
    eval_result = {"evaluated": 5, "certified": 3, "failed": 2}
    route = respx.post(f"{BASE_URL}/api/certifications/evaluate").mock(
        return_value=httpx.Response(200, json=eval_result)
    )
    result = await client.evaluate_certifications()
    assert result["evaluated"] == 5
    assert route.called


# ── Audit methods ────────────────────────────────────────────────────────────

SAMPLE_AUDIT_LOGS = {
    "results": [
        {"id": "a1", "action": "create", "resource_type": "contract"},
        {"id": "a2", "action": "update", "resource_type": "tenant"},
    ],
    "total": 2,
}


@respx.mock
@pytest.mark.asyncio
async def test_get_audit_logs_success(client):
    respx.get(f"{BASE_URL}/api/audit").mock(
        return_value=httpx.Response(200, json=SAMPLE_AUDIT_LOGS)
    )
    result = await client.get_audit_logs()
    assert "items" in result
    assert len(result["items"]) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_audit_logs_not_found(client):
    respx.get(f"{BASE_URL}/api/audit").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(DataPactNotFoundError):
        await client.get_audit_logs()


# ── Error handling ───────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_auth_error_401(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(401, json={"detail": "Invalid token"})
    )
    with pytest.raises(DataPactAuthError, match="401"):
        await client.get_contracts()


@respx.mock
@pytest.mark.asyncio
async def test_auth_error_403(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(403, json={"detail": "Forbidden"})
    )
    with pytest.raises(DataPactAuthError, match="403"):
        await client.get_contracts()


@respx.mock
@pytest.mark.asyncio
async def test_rate_limit_429(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(429, json={"detail": "Too many requests"})
    )
    with pytest.raises(DataPactRateLimitError):
        await client.get_contracts()


@respx.mock
@pytest.mark.asyncio
async def test_server_error_500(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    with pytest.raises(DataPactError, match="500"):
        await client.get_contracts()


@respx.mock
@pytest.mark.asyncio
async def test_timeout_error(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        side_effect=httpx.TimeoutException("Connection timed out")
    )
    with pytest.raises(DataPactConnectionError, match="timed out"):
        await client.get_contracts()


@respx.mock
@pytest.mark.asyncio
async def test_connect_error(client):
    respx.get(f"{BASE_URL}/api/contracts").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    with pytest.raises(DataPactConnectionError, match="connect"):
        await client.get_contracts()


# ── POST/PUT/DELETE error handling ───────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_post_auth_error(client):
    respx.post(f"{BASE_URL}/api/tenants").mock(
        return_value=httpx.Response(401, json={"detail": "Invalid token"})
    )
    with pytest.raises(DataPactAuthError):
        await client.create_tenant({"name": "Test"})


@respx.mock
@pytest.mark.asyncio
async def test_put_timeout_error(client):
    respx.put(f"{BASE_URL}/api/tenants/t1").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    with pytest.raises(DataPactConnectionError):
        await client.update_tenant("t1", {"name": "Updated"})


@respx.mock
@pytest.mark.asyncio
async def test_delete_connect_error(client):
    respx.delete(f"{BASE_URL}/api/tenants/t1").mock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(DataPactConnectionError):
        await client.delete_tenant("t1")


# ── Client defaults ──────────────────────────────────────────────────────────


def test_client_uses_config_defaults():
    """Client should use config defaults when no args provided."""
    from cmmc import config

    client = DataPactClient()
    assert client.base_url == config.DATAPACT_API_URL
    assert client.timeout == config.DATAPACT_TIMEOUT
    assert client.api_key is None


def test_client_custom_params():
    client = DataPactClient(
        base_url="http://custom:9000", api_key="mykey", timeout=10
    )
    assert client.base_url == "http://custom:9000"
    assert client.api_key == "mykey"
    assert client.timeout == 10
