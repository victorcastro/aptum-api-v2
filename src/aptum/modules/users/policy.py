"""Safeguards for managing users. Pure functions: the caller passes the locked admin count."""

from typing import Protocol

from aptum.common.enums import UserRole
from aptum.core.exceptions import ConflictError, ForbiddenError
from aptum.core.permissions import Actor
from aptum.modules.roles.policy import RoleLike


class Target(Actor, Protocol):
    is_active: bool


def check_can_manage(actor: Actor, target: Target) -> None:
    """Nobody manages themselves; only an admin manages an admin; nobody manages a user holding
    permissions they lack."""
    if actor.id == target.id:
        raise ConflictError("You cannot change your own role or status")
    if target.is_admin and not actor.is_admin:
        raise ForbiddenError("Only an admin can manage an admin")
    if not target.permissions <= actor.permissions:
        raise ForbiddenError("You cannot manage a user holding permissions you do not have")


def is_last_active_admin(target: Target, active_admins: int) -> bool:
    return target.is_admin and target.is_active and active_admins <= 1


def check_role_change(actor: Actor, target: Target, new_role: RoleLike, active_admins: int) -> None:
    check_can_manage(actor, target)
    if new_role.name == UserRole.admin and not actor.is_admin:
        raise ForbiddenError("Only an admin can grant the admin role")
    if not new_role.permission_codes <= actor.permissions:
        raise ForbiddenError("You cannot assign a role holding permissions you do not have")
    if new_role.name != UserRole.admin and is_last_active_admin(target, active_admins):
        raise ConflictError("Cannot remove the last active admin")


def check_active_change(actor: Actor, target: Target, is_active: bool, active_admins: int) -> None:
    check_can_manage(actor, target)
    if not is_active and is_last_active_admin(target, active_admins):
        raise ConflictError("Cannot deactivate the last active admin")
