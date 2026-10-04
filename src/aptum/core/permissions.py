"""Single decision point for permission-based authorization.

Routers and services ask for a `Permission`, never for a role name. Permissions are born here,
in code, because each one only guards something once an endpoint asks for it with `require`.
Roles and what they grant live in the database (`modules/roles`): `roles.sync` copies this enum
into the `permissions` table on every start and keeps `admin` holding all of them.
Data-dependent rules (e.g. "the creator may edit while unused") live in each module's
`policy.py` and build on `has_permission`.
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
    role_read = "role:read"
    role_manage = "role:manage"


# Stored in `permissions.description` by roles.sync. Every permission needs one.
PERMISSION_DESCRIPTIONS: dict[Permission, str] = {
    Permission.company_update_any: "Edit any company, even one in use",
    Permission.company_delete: "Delete companies no experience uses",
    Permission.company_merge: "Merge duplicate companies",
    Permission.skill_update_any: "Rename skills in the shared catalog",
    Permission.industry_manage: "Create and rename industries",
    Permission.user_list_read: "List users",
    Permission.user_manage_roles: "Change a user's role",
    Permission.user_deactivate: "Activate and deactivate users",
    Permission.audit_read: "Read the audit log",
    Permission.role_read: "List roles and permissions",
    Permission.role_manage: "Create, edit and delete roles",
}

_MODERATOR = frozenset(
    {
        Permission.company_update_any,
        Permission.company_delete,
        Permission.skill_update_any,
        Permission.industry_manage,
        Permission.user_list_read,
        Permission.role_read,
    }
)

# Bootstrap only: what roles.sync grants a system role when it has to create it. Once a role
# exists, its permissions are whatever an admin set (admin itself always gets everything).
DEFAULT_ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.user: frozenset(),
    UserRole.moderator: _MODERATOR,
    UserRole.admin: frozenset(Permission),
}


class HasPermissions(Protocol):
    @property
    def permissions(self) -> frozenset[str]: ...


class Actor(HasPermissions, Protocol):
    id: int

    @property
    def is_admin(self) -> bool: ...


def has_permission(user: HasPermissions, permission: Permission) -> bool:
    return permission.value in user.permissions


def require(permission: Permission) -> Callable[..., User]:
    """FastAPI dependency: the authenticated user, or 403 when their role lacks `permission`."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, permission):
            raise ForbiddenError(f"Missing permission: {permission.value}")
        return current_user

    return dependency
