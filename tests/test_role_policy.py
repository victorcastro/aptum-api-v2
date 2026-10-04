"""Who may create, edit and delete roles. Pure policy, no database."""

import pytest
from factories import actor, role

from aptum.core.exceptions import ConflictError, ForbiddenError
from aptum.modules.roles.policy import check_delete_role, check_edit_role, check_grant

ADMIN = actor("admin", 1)
MODERATOR = actor("moderator", 2)
# A custom role allowed to manage roles, holding only the catalog permissions besides.
ROLE_MANAGER = actor("role_manager", 3, permissions={"role:manage", "role:read", "skill:update_any", "industry:manage"})

EDITOR = role("catalog_editor", {"skill:update_any"})
AUDITOR = role("auditor", {"audit:read"})


def test_admin_role_is_never_edited_even_by_an_admin():
    with pytest.raises(ConflictError, match="admin role"):
        check_edit_role(ADMIN, role("admin"), [])


@pytest.mark.parametrize("name", ["user", "moderator"])
def test_only_an_admin_edits_a_system_role(name):
    check_edit_role(ADMIN, role(name), ["audit:read"])
    with pytest.raises(ForbiddenError, match="Only an admin"):
        check_edit_role(ROLE_MANAGER, role(name), [])


@pytest.mark.parametrize("name", ["user", "moderator"])
def test_system_roles_keep_their_name(name):
    with pytest.raises(ConflictError, match="renamed"):
        check_edit_role(ADMIN, role(name), [], renaming=True)


def test_custom_roles_are_edited_and_renamed_within_your_permissions():
    check_edit_role(ROLE_MANAGER, EDITOR, ["skill:update_any", "industry:manage"], renaming=True)


def test_nobody_grants_a_permission_they_lack():
    with pytest.raises(ForbiddenError, match="audit:read"):
        check_edit_role(ROLE_MANAGER, EDITOR, ["audit:read"])
    with pytest.raises(ForbiddenError, match="company:merge, user:deactivate"):
        check_grant(ROLE_MANAGER, ["user:deactivate", "company:merge", "skill:update_any"])


def test_nobody_edits_a_role_stronger_than_themselves():
    """Even only taking permissions away: shrinking a role you could not create is sabotage."""
    with pytest.raises(ForbiddenError, match="audit:read"):
        check_edit_role(ROLE_MANAGER, AUDITOR, [])


def test_system_roles_are_never_deleted():
    for name in ("user", "moderator", "admin"):
        with pytest.raises(ConflictError, match="System roles"):
            check_delete_role(ADMIN, role(name), users_count=0)


def test_a_role_in_use_is_not_deleted():
    with pytest.raises(ConflictError, match="assigned to 2 user"):
        check_delete_role(ADMIN, EDITOR, users_count=2)
    check_delete_role(ADMIN, EDITOR, users_count=0)


def test_nobody_deletes_a_role_stronger_than_themselves():
    with pytest.raises(ForbiddenError):
        check_delete_role(ROLE_MANAGER, AUDITOR, users_count=0)
    check_delete_role(ROLE_MANAGER, EDITOR, users_count=0)


def test_a_moderator_holds_no_role_manage_but_policy_alone_would_still_limit_it():
    """`role:manage` is checked by the router; the policy still caps what a moderator could do."""
    with pytest.raises(ForbiddenError):
        check_edit_role(MODERATOR, EDITOR, ["company:merge"])
