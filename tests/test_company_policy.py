"""Who may edit a shared company. Pure policy, no database."""

from types import SimpleNamespace

import pytest

from aptum.core.exceptions import ForbiddenError, NotFoundError
from aptum.modules.companies.policy import can_edit_company, check_edit_company

CREATOR_ID = 1


def user(role: str = "user", user_id: int = CREATOR_ID) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, role=role)


def company(created_by: int | None = CREATOR_ID) -> SimpleNamespace:
    return SimpleNamespace(created_by_user_id=created_by)


@pytest.mark.parametrize(
    ("actor", "target", "in_use", "allowed"),
    [
        (user(), company(), False, True),  # creator, unused
        (user(), company(), True, False),  # creator, in use
        (user("moderator", 9), company(), True, True),
        (user("admin", 9), company(), True, True),
        (user(user_id=9), company(), False, False),  # someone else
        (user(), company(created_by=None), False, False),  # creator deleted
        (user("moderator", 9), company(created_by=None), True, True),
    ],
)
def test_can_edit_company(actor, target, in_use, allowed):
    assert can_edit_company(actor, target, in_use) is allowed


def test_creator_of_used_company_gets_403():
    with pytest.raises(ForbiddenError):
        check_edit_company(user(), company(), in_use=True)


@pytest.mark.parametrize("target", [company(), company(created_by=None)])
def test_non_creator_gets_404(target):
    with pytest.raises(NotFoundError):
        check_edit_company(user(user_id=9), target, in_use=False)


def test_allowed_edit_does_not_raise():
    check_edit_company(user("moderator", 9), company(), in_use=True)
