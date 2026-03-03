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

    # ── Public methods ───────────────────────────────────────────────────

    async def get_contracts(self) -> dict[str, Any]:
        """List all contracts."""
        return await self._get("/api/contracts")

    async def get_contract(self, contract_id: str) -> dict[str, Any]:
        """Get a single contract by ID."""
        return await self._get(f"/api/contracts/{contract_id}")

    async def get_contract_compliance(self, contract_id: str) -> dict[str, Any]:
        """Get compliance data for a contract."""
        return await self._get(f"/api/contracts/{contract_id}/compliance")

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _get(self, path: str) -> dict[str, Any]:
        """Execute a GET request and handle errors."""
        headers: dict[str, str] = {}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.timeout
            ) as http:
                response = await http.get(path, headers=headers)
        except httpx.TimeoutException as exc:
            raise DataPactConnectionError(
                f"DataPact request timed out: {exc}", status_code=None
            ) from exc
        except httpx.ConnectError as exc:
            raise DataPactConnectionError(
                f"Could not connect to DataPact: {exc}", status_code=None
            ) from exc

        self._raise_for_status(response, path)
        return response.json()

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
