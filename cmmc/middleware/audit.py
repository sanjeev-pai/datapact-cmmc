"""Audit logging middleware — records write operations to the audit_log table."""

import logging
from typing import Any

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from cmmc import config

logger = logging.getLogger(__name__)

# HTTP methods considered "write" operations
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths to skip auditing (noisy or non-business endpoints)
_SKIP_PREFIXES = ("/api/health", "/api/auth/refresh")


def _extract_user_id(request: Request) -> str | None:
    """Extract user_id from JWT Authorization header without DB lookup."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except (jwt.PyJWTError, Exception):
        return None


def _extract_resource(path: str) -> tuple[str, str | None]:
    """Derive resource_type and resource_id from the URL path.

    Examples:
        /api/assessments          -> ("assessments", None)
        /api/assessments/abc123   -> ("assessments", "abc123")
        /api/poams/x/items/y      -> ("poams", "x")
    """
    parts = path.strip("/").split("/")
    # Skip leading "api" segment
    if parts and parts[0] == "api":
        parts = parts[1:]
    resource_type = parts[0] if parts else "unknown"
    resource_id = parts[1] if len(parts) > 1 else None
    return resource_type, resource_id


def _action_from_method(method: str) -> str:
    """Map HTTP method to an action verb."""
    return {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }.get(method, method.lower())


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs write operations (POST/PUT/PATCH/DELETE) to the audit_log table."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only audit write methods on /api/ paths
        if (
            request.method not in _WRITE_METHODS
            or not request.url.path.startswith("/api/")
        ):
            return await call_next(request)

        # Skip noisy endpoints
        for prefix in _SKIP_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        response = await call_next(request)

        # Only log successful writes (2xx status codes)
        if 200 <= response.status_code < 300:
            try:
                self._write_audit_log(request, response)
            except Exception:
                logger.exception("Failed to write audit log")

        return response

    def _write_audit_log(self, request: Request, response: Response) -> None:
        from cmmc.database import SessionLocal
        from cmmc.models.audit import AuditLog

        user_id = _extract_user_id(request)
        resource_type, resource_id = _extract_resource(request.url.path)
        action = _action_from_method(request.method)
        ip = request.client.host if request.client else None

        # Build details dict
        details: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        }
        if request.url.query:
            details["query"] = request.url.query

        db = SessionLocal()
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
