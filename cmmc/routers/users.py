"""User management (admin) API endpoints."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user
from cmmc.errors import ConflictError, ForbiddenError, NotFoundError
from cmmc.models.user import Role, User, UserRole
from cmmc.schemas.user import UserAdminResponse, UserAdminUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _check_admin_access(caller: User, target: User) -> None:
    """Verify caller has admin access to the target user.

    - system_admin: access to any user
    - org_admin: access only to users in the same org
    - others: denied
    """
    caller_roles = {r.name for r in caller.roles}

    if "system_admin" in caller_roles:
        return

    if "org_admin" in caller_roles and caller.org_id and caller.org_id == target.org_id:
        return

    raise ForbiddenError("Insufficient permissions")


@router.get("", response_model=list[UserAdminResponse])
def list_users(
    caller: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List users. system_admin sees all; org_admin sees own org only."""
    caller_roles = {r.name for r in caller.roles}

    if "system_admin" in caller_roles:
        users = db.query(User).order_by(User.username).all()
    elif "org_admin" in caller_roles and caller.org_id:
        users = db.query(User).filter(User.org_id == caller.org_id).order_by(User.username).all()
    else:
        raise ForbiddenError("Insufficient permissions")

    return [UserAdminResponse.from_user(u) for u in users]


@router.get("/{user_id}", response_model=UserAdminResponse)
def get_user(
    user_id: str,
    caller: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user detail. system_admin can view any; org_admin can view own org only."""
    caller_roles = {r.name for r in caller.roles}

    if "system_admin" not in caller_roles and "org_admin" not in caller_roles:
        raise ForbiddenError("Insufficient permissions")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise NotFoundError("User not found")

    _check_admin_access(caller, target)
    return UserAdminResponse.from_user(target)


@router.patch("/{user_id}", response_model=UserAdminResponse)
def update_user(
    user_id: str,
    body: UserAdminUpdate,
    caller: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user. system_admin can update any; org_admin can update own org users."""
    caller_roles = {r.name for r in caller.roles}

    if "system_admin" not in caller_roles and "org_admin" not in caller_roles:
        raise ForbiddenError("Insufficient permissions")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise NotFoundError("User not found")

    _check_admin_access(caller, target)

    is_system_admin = "system_admin" in caller_roles

    # org_admin restrictions
    if not is_system_admin:
        if body.org_id is not None and body.org_id != target.org_id:
            raise ForbiddenError("org_admin cannot change user org assignment")
        if body.roles is not None and "system_admin" in body.roles:
            raise ForbiddenError("org_admin cannot assign system_admin role")

    # Update username
    if body.username is not None and body.username != target.username:
        if db.query(User).filter(User.username == body.username, User.id != target.id).first():
            raise ConflictError("Username already taken")
        target.username = body.username

    # Update email
    if body.email is not None and body.email != target.email:
        if db.query(User).filter(User.email == body.email, User.id != target.id).first():
            raise ConflictError("Email already taken")
        target.email = body.email

    # Update is_active
    if body.is_active is not None:
        target.is_active = body.is_active

    # Update org_id (system_admin only, enforced above)
    if body.org_id is not None:
        target.org_id = body.org_id

    # Update roles
    if body.roles is not None:
        # Validate all role names exist
        new_roles = []
        for role_name in body.roles:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                raise NotFoundError(f"Role '{role_name}' not found")
            new_roles.append(role)

        # Remove existing role assignments
        db.query(UserRole).filter(UserRole.user_id == target.id).delete()
        db.flush()

        # Add new role assignments
        for role in new_roles:
            db.add(UserRole(user_id=target.id, role_id=role.id))

    db.commit()
    db.refresh(target)
    return UserAdminResponse.from_user(target)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: str,
    caller: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a user (soft delete). Cannot deactivate yourself."""
    caller_roles = {r.name for r in caller.roles}

    if "system_admin" not in caller_roles and "org_admin" not in caller_roles:
        raise ForbiddenError("Insufficient permissions")

    if caller.id == user_id:
        raise ForbiddenError("Cannot deactivate yourself")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise NotFoundError("User not found")

    _check_admin_access(caller, target)

    target.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
