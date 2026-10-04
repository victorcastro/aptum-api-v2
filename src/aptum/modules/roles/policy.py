"""Who may create, edit and delete roles. Pure functions: no database.

The anti-escalation rule runs through every write: nobody hands out, takes away or deletes
permissions they do not hold themselves. Admin holds them all, so it is never limited by it.
"""

from collections.abc import Iterable
from typing import Protocol

from aptum.common.enums import UserRole
from aptum.core.exceptions import ConflictError, ForbiddenError
from aptum.core.permissions import Actor


class RoleLike(Protocol):
    name: str
    is_system: bool

    @property
    def permission_codes(self) -> frozenset[str]: ...


def check_grant(actor: Actor, codes: Iterable[str]) -> None:
    missing = set(codes) - actor.permissions
    if missing:
        raise ForbiddenError(f"You do not hold these permissions: {', '.join(sorted(missing))}")


def check_edit_role(actor: Actor, role: RoleLike, new_codes: Iterable[str], *, renaming: bool = False) -> None:
    """The admin role is fixed (409). System roles: only an admin edits them (403) and nobody
    renames them (409). Any role: both its current and new permissions must be held by the actor."""
    if role.name == UserRole.admin:
        raise ConflictError("The admin role always holds every permission and cannot be edited")
    if role.is_system and not actor.is_admin:
        raise ForbiddenError("Only an admin can edit a system role")
    if role.is_system and renaming:
        raise ConflictError("System roles cannot be renamed")
    check_grant(actor, role.permission_codes | set(new_codes))


def check_delete_role(actor: Actor, role: RoleLike, users_count: int) -> None:
    if role.is_system:
        raise ConflictError("System roles cannot be deleted")
    check_grant(actor, role.permission_codes)
    if users_count:
        raise ConflictError(f"Role is assigned to {users_count} user(s); give them another role first")
