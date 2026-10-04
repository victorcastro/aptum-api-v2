"""Role x permission matrix and the `require` dependency. No database."""

from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from aptum.common.enums import UserRole
from aptum.core.dependencies import get_current_user
from aptum.core.exceptions import register_exception_handlers
from aptum.core.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    has_permission,
    permissions_for,
    require,
)

P = Permission
EXPECTED = {
    UserRole.user: set(),
    UserRole.moderator: {
        P.company_update_any,
        P.company_delete,
        P.skill_update_any,
        P.industry_manage,
        P.user_list_read,
    },
    UserRole.admin: set(P),
}


def test_every_role_has_an_entry():
    assert set(ROLE_PERMISSIONS) == set(UserRole)


@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.parametrize("permission", list(Permission))
def test_matrix(role, permission):
    user = SimpleNamespace(role=role.value)
    assert has_permission(user, permission) is (permission in EXPECTED[role])


def test_unknown_role_gets_nothing():
    assert permissions_for("root") == frozenset()


def test_admin_is_a_superset_of_moderator():
    assert ROLE_PERMISSIONS[UserRole.moderator] < ROLE_PERMISSIONS[UserRole.admin]


@pytest.fixture
def make_client():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/guarded")
    def guarded(user=Depends(require(Permission.audit_read))):
        return {"id": user.id}

    def factory(role: str) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, role=role)
        return TestClient(app)

    return factory


def test_require_lets_the_permission_through(make_client):
    response = make_client("admin").get("/guarded")
    assert response.status_code == 200 and response.json() == {"id": 7}


@pytest.mark.parametrize("role", ["user", "moderator"])
def test_require_rejects_with_403_and_detail(make_client, role):
    response = make_client(role).get("/guarded")
    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: audit:read"}
