"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.errors import ForbiddenError, UnauthorizedError
from cmmc.models.user import User
from cmmc.services.auth_service import decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header, return the User.

    Raises UnauthorizedError (401) when:
    - No Authorization header / empty token
    - Token is invalid or expired
    - Token is not an access token
    - User does not exist or is inactive
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing authentication token")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return user


def require_role(*roles: str):
    """Dependency factory: require the current user to have at least one of the given roles.

    Usage::

        @router.get("/admin")
        def admin_only(user: User = Depends(require_role("system_admin", "org_admin"))):
            ...

    Raises ForbiddenError (403) if the user lacks all listed roles.
    """

    def _check(user: User = Depends(get_current_user)) -> User:
        user_roles = {r.name for r in user.roles}
        if not user_roles.intersection(roles):
            raise ForbiddenError("Insufficient permissions")
        return user

    return _check


class PermissionChecker:
    """Callable dependency for fine-grained permission checks.

    Supports role-based gating. Can be extended with org-scope or
    resource-level checks in future phases.

    Usage::

        @router.get("/resource")
        def protected(user: User = Depends(PermissionChecker(roles=["org_admin"]))):
            ...
    """

    def __init__(self, roles: list[str] | None = None):
        self.roles = set(roles) if roles else set()

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if self.roles:
            user_roles = {r.name for r in user.roles}
            if not user_roles.intersection(self.roles):
                raise ForbiddenError("Insufficient permissions")
        return user
