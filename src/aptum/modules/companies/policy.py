"""Data-dependent rules for the shared company catalog. Pure functions: no database."""

from typing import Protocol

from aptum.core.exceptions import ForbiddenError, NotFoundError
from aptum.core.permissions import Actor, Permission, has_permission


class CompanyLike(Protocol):
    created_by_user_id: int | None


def can_edit_company(user: Actor, company: CompanyLike, in_use: bool) -> bool:
    """Moderators and admins edit any company. The creator edits it only while no experience uses it."""
    if has_permission(user, Permission.company_update_any):
        return True
    return company.created_by_user_id == user.id and not in_use


def check_edit_company(user: Actor, company: CompanyLike, in_use: bool) -> None:
    """Raise like the API answers: 404 when the caller has no claim on the company, 403 when
    the creator tries to edit it after someone used it."""
    if can_edit_company(user, company, in_use):
        return
    if company.created_by_user_id != user.id:
        raise NotFoundError("Company not found")
    raise ForbiddenError("Company is in use by experiences; only a moderator can edit it")
