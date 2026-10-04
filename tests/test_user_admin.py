"""User management: pure safeguards and the /admin/users endpoints over a fake session."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from factories import FakeSession, actor, role
from fastapi.testclient import TestClient

from aptum.common.enums import UserRole
from aptum.core.dependencies import get_current_user, get_db
from aptum.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.users.admin_service import UserAdminService
from aptum.modules.users.models import User
from aptum.modules.users.policy import (
    check_active_change,
    check_can_manage,
    check_role_change,
)
from aptum.modules.users.repository import UserRepository

ADMIN = actor("admin", 1)
OTHER_ADMIN = actor("admin", 2)
MODERATOR = actor("moderator", 3)
PLAIN = actor("user", 4)
# A custom role that may manage roles but holds no catalog permissions.
USER_MANAGER = actor("user_manager", 5, permissions={"user:list_read", "user:manage_roles", "user:deactivate"})

USER_ROLE, MODERATOR_ROLE, ADMIN_ROLE = role("user"), role("moderator"), role("admin")


# --- pure safeguards -------------------------------------------------------------------------


@pytest.mark.parametrize("actor", [ADMIN, MODERATOR, PLAIN])
def test_nobody_manages_themselves(actor):
    with pytest.raises(ConflictError):
        check_can_manage(actor, actor)


def test_moderator_never_touches_an_admin():
    with pytest.raises(ForbiddenError):
        check_role_change(MODERATOR, OTHER_ADMIN, USER_ROLE, active_admins=2)
    with pytest.raises(ForbiddenError):
        check_active_change(MODERATOR, OTHER_ADMIN, False, active_admins=2)


def test_moderator_cannot_grant_admin():
    with pytest.raises(ForbiddenError):
        check_role_change(MODERATOR, PLAIN, ADMIN_ROLE, active_admins=1)


def test_nobody_assigns_a_role_holding_permissions_they_lack():
    with pytest.raises(ForbiddenError, match="assign a role"):
        check_role_change(USER_MANAGER, PLAIN, MODERATOR_ROLE, active_admins=1)
    check_role_change(USER_MANAGER, PLAIN, role("viewer", {"user:list_read"}), active_admins=1)


def test_nobody_manages_a_user_holding_permissions_they_lack():
    with pytest.raises(ForbiddenError, match="holding permissions"):
        check_role_change(USER_MANAGER, MODERATOR, USER_ROLE, active_admins=1)
    with pytest.raises(ForbiddenError, match="holding permissions"):
        check_active_change(USER_MANAGER, MODERATOR, False, active_admins=1)
    check_active_change(USER_MANAGER, PLAIN, False, active_admins=1)


def test_last_active_admin_cannot_be_demoted_or_deactivated():
    with pytest.raises(ConflictError, match="last active admin"):
        check_role_change(ADMIN, OTHER_ADMIN, MODERATOR_ROLE, active_admins=1)
    with pytest.raises(ConflictError, match="last active admin"):
        check_active_change(ADMIN, OTHER_ADMIN, False, active_admins=1)


def test_admin_demotes_another_admin_when_one_remains():
    check_role_change(ADMIN, OTHER_ADMIN, USER_ROLE, active_admins=2)
    check_active_change(ADMIN, OTHER_ADMIN, False, active_admins=2)


def test_inactive_admin_does_not_count_as_the_last_one():
    inactive_admin = actor("admin", 5, is_active=False)
    check_role_change(ADMIN, inactive_admin, USER_ROLE, active_admins=1)


def test_keeping_the_admin_role_is_never_blocked():
    check_role_change(ADMIN, OTHER_ADMIN, ADMIN_ROLE, active_admins=1)
    check_active_change(ADMIN, OTHER_ADMIN, True, active_admins=1)


# --- endpoints -------------------------------------------------------------------------------


ROLES = {r.name: r for r in (USER_ROLE, MODERATOR_ROLE, ADMIN_ROLE, role("catalog_editor", {"skill:update_any"}))}


def db_user(user_id: int, role_name: str, is_active: bool = True) -> User:
    return User(
        id=user_id,
        email=f"u{user_id}@example.com",
        role=ROLES[role_name],
        role_id=ROLES[role_name].id,
        is_active=is_active,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def world(monkeypatch):
    users = {1: db_user(1, "admin"), 2: db_user(2, "admin"), 4: db_user(4, "user")}
    state = SimpleNamespace(users=users, audit=[], session=FakeSession(), locks=[])

    def lock_admins(self):
        state.locks.append("admins")
        return [u.id for u in users.values() if u.is_admin and u.is_active]

    def get_for_update(self, user_id):
        state.locks.append(user_id)
        return users.get(user_id)

    monkeypatch.setattr(UserRepository, "lock_active_admin_ids", lock_admins)
    monkeypatch.setattr(UserRepository, "get_for_update", get_for_update)
    monkeypatch.setattr(RoleRepository, "get_by_name", lambda self, name: ROLES.get(name))
    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: state.audit.append(entry))
    app.dependency_overrides[get_db] = lambda: state.session
    yield state
    app.dependency_overrides.clear()


def as_user(actor) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: actor
    return TestClient(app)


def test_admin_promotes_a_user_and_it_is_audited(world):
    response = as_user(world.users[1]).patch("/admin/users/4/role", json={"role": "moderator"})
    assert response.status_code == 200 and response.json()["role"] == "moderator"
    [entry] = world.audit
    assert (entry.actor_user_id, entry.action, entry.entity_type, entry.entity_id) == (1, "user.role_change", "user", 4)
    assert entry.changes == {"role": {"before": "user", "after": "moderator"}}
    assert world.locks == ["admins", 4]  # admin rows locked before the target, every time
    assert world.session.commits == 1


def test_same_role_is_a_noop_without_audit(world):
    assert as_user(world.users[1]).patch("/admin/users/4/role", json={"role": "user"}).status_code == 200
    assert world.audit == []


def test_admin_cannot_change_own_role(world):
    response = as_user(world.users[1]).patch("/admin/users/1/role", json={"role": "user"})
    assert response.status_code == 409
    assert response.json() == {"detail": "You cannot change your own role or status"}
    assert world.audit == [] and world.session.commits == 0


def test_admin_cannot_deactivate_self(world):
    assert as_user(world.users[1]).patch("/admin/users/1/active", json={"is_active": False}).status_code == 409


def test_deactivation_is_audited(world):
    response = as_user(world.users[1]).patch("/admin/users/2/active", json={"is_active": False})
    assert response.status_code == 200 and response.json()["is_active"] is False
    [entry] = world.audit
    assert entry.action == "user.deactivate"
    assert entry.changes == {"is_active": {"before": True, "after": False}}


def test_endpoint_refuses_to_remove_the_last_active_admin(world):
    # Admin 1 deactivated meanwhile: admin 2 is the only active admin left under the lock.
    # The actor stands for a session whose admin row changed after authentication.
    world.users[1].is_active = False
    stale_admin = actor("admin", 9)
    for path, body in (("/admin/users/2/role", {"role": "user"}), ("/admin/users/2/active", {"is_active": False})):
        response = as_user(stale_admin).patch(path, json=body)
        assert response.status_code == 409 and "last active admin" in response.json()["detail"]
    assert world.audit == []


def test_admin_assigns_a_custom_role(world):
    response = as_user(world.users[1]).patch("/admin/users/4/role", json={"role": "catalog_editor"})
    assert response.status_code == 200 and response.json()["role"] == "catalog_editor"
    assert world.users[4].permissions == {"skill:update_any"}
    [entry] = world.audit
    assert entry.changes == {"role": {"before": "user", "after": "catalog_editor"}}


def test_unknown_user_is_404(world):
    assert as_user(world.users[1]).patch("/admin/users/99/role", json={"role": "user"}).status_code == 404


def test_unknown_role_is_404_before_locking(world):
    response = as_user(world.users[1]).patch("/admin/users/4/role", json={"role": "root"})
    assert response.status_code == 404 and response.json() == {"detail": "Role not found"}
    assert world.locks == []


def test_empty_role_name_is_422(world):
    assert as_user(world.users[1]).patch("/admin/users/4/role", json={"role": ""}).status_code == 422


def test_role_manager_without_catalog_permissions_cannot_promote_to_moderator(world):
    response = as_user(USER_MANAGER).patch("/admin/users/4/role", json={"role": "moderator"})
    assert response.status_code == 403 and "assign a role" in response.json()["detail"]
    assert world.audit == [] and world.session.commits == 0


@pytest.mark.parametrize(
    ("role", "path", "body"),
    [
        ("moderator", "/admin/users/4/role", {"role": "moderator"}),
        ("moderator", "/admin/users/4/active", {"is_active": False}),
        ("user", "/admin/users/4/role", {"role": "admin"}),
    ],
)
def test_writes_need_the_admin_permissions(world, role, path, body):
    response = as_user(actor(role, 3)).patch(path, json=body)
    assert response.status_code == 403 and response.json()["detail"].startswith("Missing permission")
    assert world.locks == []  # rejected before touching the database


def test_moderator_lists_users_with_filters(world, monkeypatch):
    seen = {}

    def list_page(self, **filters):
        seen.update(filters)
        return [world.users[4]], 1

    monkeypatch.setattr(UserRepository, "list_page", list_page)
    response = as_user(actor("moderator", 3)).get(
        "/admin/users", params={"role": "user", "is_active": "true", "q": "u4"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 4,
                "email": "u4@example.com",
                "is_active": True,
                "role": "user",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
        "total": 1,
    }
    assert seen == {"role": "user", "is_active": True, "email_query": "u4", "limit": 20, "offset": 0}


def test_plain_user_cannot_list_users(world):
    assert as_user(actor("user", 4)).get("/admin/users").status_code == 403


# --- operator bootstrap (CLI / seeder) ---------------------------------------------------------


@pytest.fixture
def operator(world, monkeypatch):
    by_email = {u.email: u for u in world.users.values()}
    monkeypatch.setattr(UserRepository, "get_by_email_for_update", lambda self, email: by_email.get(email))
    return UserAdminService(world.session)


def test_operator_promotes_the_first_admin_with_no_actor(world, operator):
    user = operator.set_role_by_operator("u4@example.com", UserRole.admin)
    assert user.role_name == "admin"
    [entry] = world.audit
    assert entry.actor_user_id is None
    assert entry.changes == {"role": {"before": "user", "after": "admin"}, "via": "operator"}


def test_operator_cannot_remove_the_last_active_admin(world, operator):
    world.users[2].is_active = False
    with pytest.raises(ConflictError):
        operator.set_role_by_operator("u1@example.com", UserRole.user)


def test_operator_unknown_email_is_not_found(world, operator):
    with pytest.raises(NotFoundError):
        operator.set_role_by_operator("ghost@example.com", UserRole.admin)
