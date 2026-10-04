"""Single decision point for role-based authorization.

Routers and services ask for a `Permission`, never for a role name. This module is the only
place that knows which role grants what, so it can be swapped for a policy engine later
without touching callers. Data-dependent rules (e.g. "the creator may edit while unused") live
in each module's `policy.py` and build on `has_permission`.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

from fastapi import Depends

from aptum.common.enums import UserRole
from aptum.core.dependencies import get_current_user
from aptum.core.exceptions import ForbiddenError
from aptum.modules.users.models import User


class Permission(StrEnum):
    company_update_any = "company:update_any"
    company_delete = "company:delete"
    company_merge = "company:merge"
    skill_update_any = "skill:update_any"
    industry_manage = "industry:manage"
    user_list_read = "user:list_read"
    user_manage_roles = "user:manage_roles"
    user_deactivate = "user:deactivate"
    audit_read = "audit:read"


_MODERATOR = frozenset(
    {
        Permission.company_update_any,
        Permission.company_delete,
        Permission.skill_update_any,
        Permission.industry_manage,
        Permission.user_list_read,
    }
)

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.user: frozenset(),
    UserRole.moderator: _MODERATOR,
    UserRole.admin: _MODERATOR
    | {
        Permission.company_merge,
        Permission.user_manage_roles,
        Permission.user_deactivate,
        Permission.audit_read,
    },
}


class HasRole(Protocol):
    role: str


def permissions_for(role: str) -> frozenset[Permission]:
    """Unknown roles get nothing (safe default)."""
    try:
        return ROLE_PERMISSIONS[UserRole(role)]
    except ValueError:
        return frozenset()


def has_permission(user: HasRole, permission: Permission) -> bool:
    return permission in permissions_for(user.role)


def require(permission: Permission) -> Callable[..., User]:
    """FastAPI dependency: the authenticated user, or 403 when the role lacks `permission`."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, permission):
            raise ForbiddenError(f"Missing permission: {permission.value}")
        return current_user

    return dependency
