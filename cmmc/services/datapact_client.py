"""HTTP client for the DataPact contract-management API."""

from __future__ import annotations

from typing import Any

import httpx

from cmmc import config


# ── Custom exceptions ────────────────────────────────────────────────────────


class DataPactError(Exception):
    """Base exception for DataPact API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class DataPactConnectionError(DataPactError):
    """Raised on timeout or connection failure."""


class DataPactAuthError(DataPactError):
    """Raised on 401/403 authentication/authorization failures."""


class DataPactNotFoundError(DataPactError):
    """Raised when the requested resource is not found (404)."""


class DataPactRateLimitError(DataPactError):
    """Raised when the API returns 429 Too Many Requests."""


# ── Client ───────────────────────────────────────────────────────────────────


class DataPactClient:
    """Async HTTP client for DataPact REST API.

    Parameters
    ----------
    base_url : str | None
        DataPact API base URL. Defaults to ``config.DATAPACT_API_URL``.
    api_key : str | None
        Bearer token for authentication. ``None`` means no auth header.
    timeout : int | None
        Request timeout in seconds. Defaults to ``config.DATAPACT_TIMEOUT``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.base_url = base_url or config.DATAPACT_API_URL
        self.api_key = api_key
        self.timeout = timeout if timeout is not None else config.DATAPACT_TIMEOUT

    # ── Contract methods ──────────────────────────────────────────────

    async def get_contracts(self, **params: Any) -> dict[str, Any]:
        """List all contracts. Normalizes ``results`` key to ``items``."""
        data = await self._get("/api/contracts", params=params)
        return _normalize_list_response(data)

    async def get_contract(self, contract_id: str) -> dict[str, Any]:
        """Get a single contract by ID."""
        return await self._get(f"/api/contracts/{contract_id}")

    async def get_contract_compliance(self, contract_id: str) -> dict[str, Any]:
        """Get compliance data for a contract."""
        return await self._get(f"/api/contracts/{contract_id}/compliance")

    # ── Tenant/Organization methods ───────────────────────────────────

    async def get_tenants(self, **params: Any) -> dict[str, Any]:
        """List all tenants. Normalizes ``results`` key to ``items``."""
        data = await self._get("/api/tenants", params=params)
        return _normalize_list_response(data)

    async def get_tenant(self, tenant_id: str) -> dict[str, Any]:
        """Get a single tenant by ID."""
        return await self._get(f"/api/tenants/{tenant_id}")

    async def create_tenant(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new tenant."""
        return await self._post("/api/tenants", json=data)

    async def update_tenant(self, tenant_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing tenant."""
        return await self._put(f"/api/tenants/{tenant_id}", json=data)

    async def delete_tenant(self, tenant_id: str) -> None:
        """Delete a tenant."""
        await self._delete(f"/api/tenants/{tenant_id}")

    # ── Compliance Scoring methods ────────────────────────────────────

    async def get_compliance_scores(self, **params: Any) -> dict[str, Any]:
        """List compliance scores across contracts."""
        data = await self._get("/api/compliance/scores", params=params)
        return _normalize_list_response(data)

    async def get_compliance_score(self, contract_id: str) -> dict[str, Any]:
        """Get compliance score for a specific contract."""
        return await self._get(f"/api/compliance/scores/{contract_id}")

    async def get_org_compliance_score(self) -> dict[str, Any]:
        """Get org-level aggregate compliance score."""
        return await self._get("/api/compliance/scores/org")

    # ── Certification methods ─────────────────────────────────────────

    async def get_certifications(self, **params: Any) -> dict[str, Any]:
        """List certifications with optional filters."""
        data = await self._get("/api/certifications", params=params)
        return _normalize_list_response(data)

    async def get_certification(self, contract_id: str) -> dict[str, Any]:
        """Get certification status for a specific contract."""
        return await self._get(f"/api/certifications/{contract_id}")

    async def evaluate_certifications(self) -> dict[str, Any]:
        """Trigger certification evaluation."""
        return await self._post("/api/certifications/evaluate")

    # ── Audit methods ─────────────────────────────────────────────────

    async def get_audit_logs(self, **params: Any) -> dict[str, Any]:
        """List audit log entries with optional filters."""
        data = await self._get("/api/audit", params=params)
        return _normalize_list_response(data)

    # ── Internal HTTP methods ─────────────────────────────────────────

    def _build_headers(self) -> dict[str, str]:
        """Build request headers including auth if configured."""
        headers: dict[str, str] = {}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request and handle connection errors."""
        headers = self._build_headers()
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout
            ) as http:
                response = await http.request(
                    method, path, headers=headers, params=params, json=json
                )
        except httpx.TimeoutException as exc:
            raise DataPactConnectionError(
                f"DataPact request timed out: {exc}", status_code=None
            ) from exc
        except httpx.ConnectError as exc:
            raise DataPactConnectionError(
                f"Could not connect to DataPact: {exc}", status_code=None
            ) from exc

        self._raise_for_status(response, path)
        return response

    async def _get(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GET request and return JSON."""
        response = await self._request("GET", path, params=params)
        return response.json()

    async def _post(
        self, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a POST request and return JSON."""
        response = await self._request("POST", path, json=json)
        return response.json()

    async def _put(
        self, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a PUT request and return JSON."""
        response = await self._request("PUT", path, json=json)
        return response.json()

    async def _delete(self, path: str) -> None:
        """Execute a DELETE request (no response body expected)."""
        await self._request("DELETE", path)

    @staticmethod
    def _raise_for_status(response: httpx.Response, path: str) -> None:
        """Map HTTP error codes to typed exceptions."""
        code = response.status_code
        if 200 <= code < 300:
            return

        # Try to extract detail from JSON body
        detail = ""
        try:
            body = response.json()
            detail = body.get("detail", "")
        except Exception:
            detail = response.text[:200]

        if code in (401, 403):
            raise DataPactAuthError(
                f"DataPact auth error {code} on {path}: {detail}",
                status_code=code,
            )
        if code == 404:
            raise DataPactNotFoundError(
                f"DataPact resource not found: {path}",
                status_code=404,
            )
        if code == 429:
            raise DataPactRateLimitError(
                f"DataPact rate limit exceeded on {path}: {detail}",
                status_code=429,
            )
        raise DataPactError(
            f"DataPact error {code} on {path}: {detail}",
            status_code=code,
        )


def _normalize_list_response(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize DataPact list responses: ``results`` → ``items``.

    DataPact returns ``{results: [...], total, ...}`` but CMMC code
    expects ``{items: [...], total, ...}``.
    """
    if "results" in data and "items" not in data:
        data["items"] = data.pop("results")
    return data
