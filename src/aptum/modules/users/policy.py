"""Safeguards for managing users. Pure functions: the caller passes the locked admin count."""

from typing import Protocol

from aptum.common.enums import UserRole
from aptum.core.exceptions import ConflictError, ForbiddenError
from aptum.core.permissions import Actor


class Target(Actor, Protocol):
    is_active: bool


def check_can_manage(actor: Actor, target: Target) -> None:
    """Nobody manages themselves; only an admin manages an admin."""
    if actor.id == target.id:
        raise ConflictError("You cannot change your own role or status")
    if target.role == UserRole.admin and actor.role != UserRole.admin:
        raise ForbiddenError("Only an admin can manage an admin")


def _is_last_active_admin(target: Target, active_admins: int) -> bool:
    return target.role == UserRole.admin and target.is_active and active_admins <= 1


def check_role_change(actor: Actor, target: Target, new_role: UserRole, active_admins: int) -> None:
    check_can_manage(actor, target)
    if new_role == UserRole.admin and actor.role != UserRole.admin:
        raise ForbiddenError("Only an admin can grant the admin role")
    if new_role != UserRole.admin and _is_last_active_admin(target, active_admins):
        raise ConflictError("Cannot remove the last active admin")


def check_active_change(actor: Actor, target: Target, is_active: bool, active_admins: int) -> None:
    check_can_manage(actor, target)
    if not is_active and _is_last_active_admin(target, active_admins):
        raise ConflictError("Cannot deactivate the last active admin")
