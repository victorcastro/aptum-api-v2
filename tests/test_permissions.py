"""Permission checks, the bootstrap grants and the `require` dependency. No database."""

import pytest
from factories import actor, role
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from aptum.common.enums import UserRole
from aptum.core.dependencies import get_current_user
from aptum.core.exceptions import register_exception_handlers
from aptum.core.permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSION_DESCRIPTIONS,
    Permission,
    has_permission,
    require,
)
from aptum.modules.users.models import User

P = Permission
EXPECTED = {
    UserRole.user: set(),
    UserRole.moderator: {
        P.company_update_any,
        P.company_delete,
        P.skill_update_any,
        P.industry_manage,
        P.user_list_read,
        P.role_read,
    },
    UserRole.admin: set(P),
}


def test_every_system_role_has_defaults():
    assert set(DEFAULT_ROLE_PERMISSIONS) == set(UserRole)


def test_every_permission_has_a_description():
    assert set(PERMISSION_DESCRIPTIONS) == set(Permission)
    assert all(0 < len(text) <= 255 for text in PERMISSION_DESCRIPTIONS.values())


@pytest.mark.parametrize("role_name", list(UserRole))
@pytest.mark.parametrize("permission", list(Permission))
def test_default_matrix(role_name, permission):
    assert has_permission(actor(role_name), permission) is (permission in EXPECTED[role_name])


def test_admin_defaults_are_a_superset_of_moderator():
    assert DEFAULT_ROLE_PERMISSIONS[UserRole.moderator] < DEFAULT_ROLE_PERMISSIONS[UserRole.admin]


def test_a_custom_role_grants_exactly_its_permissions():
    editor = actor("catalog_editor", permissions={"skill:update_any"})
    assert has_permission(editor, P.skill_update_any)
    assert not has_permission(editor, P.industry_manage)
    assert editor.is_admin is False


def test_user_reads_permissions_from_its_role_row():
    user = User(id=1, email="u@example.com", role=role("catalog_editor", {"industry:manage"}))
    assert user.permissions == frozenset({"industry:manage"})
    assert user.role_name == "catalog_editor" and user.is_admin is False
    assert User(id=2, email="a@example.com", role=role("admin")).is_admin is True


@pytest.fixture
def make_client():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/guarded")
    def guarded(user=Depends(require(Permission.audit_read))):
        return {"id": user.id}

    def factory(role_name: str, permissions=None) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: actor(role_name, 7, permissions=permissions)
        return TestClient(app)

    return factory


def test_require_lets_the_permission_through(make_client):
    response = make_client("admin").get("/guarded")
    assert response.status_code == 200 and response.json() == {"id": 7}


def test_require_trusts_the_role_permissions_not_its_name(make_client):
    assert make_client("auditor", {"audit:read"}).get("/guarded").status_code == 200
    assert make_client("admin", set()).get("/guarded").status_code == 403


@pytest.mark.parametrize("role_name", ["user", "moderator"])
def test_require_rejects_with_403_and_detail(make_client, role_name):
    response = make_client(role_name).get("/guarded")
    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: audit:read"}
