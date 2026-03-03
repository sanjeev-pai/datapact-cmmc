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
