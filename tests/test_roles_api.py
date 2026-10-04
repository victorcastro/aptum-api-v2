"""The /admin/roles and /admin/permissions endpoints over stubbed repositories."""

from types import SimpleNamespace

import pytest
from factories import FakeSession, actor, role
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from aptum.core.dependencies import get_current_user, get_db
from aptum.core.permissions import PERMISSION_DESCRIPTIONS
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.roles.models import PermissionRecord, Role
from aptum.modules.roles.repository import RoleRepository

ADMIN = actor("admin", 1)
MODERATOR = actor("moderator", 2)
ROLE_MANAGER = actor("role_manager", 3, permissions={"role:manage", "role:read", "skill:update_any", "industry:manage"})


@pytest.fixture
def world(monkeypatch):
    catalog = {p.value: PermissionRecord(id=i, code=p.value, description=d) for i, (p, d) in enumerate(PERMISSION_DESCRIPTIONS.items(), 1)}
    roles = {
        r.id: r
        for r in (role("user"), role("moderator"), role("admin"), role("catalog_editor", {"skill:update_any"}, role_id=10))
    }
    for r in roles.values():  # share the catalog rows, as the session would
        r.permissions = [catalog[p.code] for p in r.permissions]
    state = SimpleNamespace(roles=roles, counts={1: 5, 2: 1, 3: 1}, audit=[], deleted=[], session=FakeSession())

    def create(self, name, description, permissions, *, is_system=False):
        if any(r.name == name for r in roles.values()):
            raise IntegrityError("INSERT", {}, Exception("duplicate"))
        roles[20] = Role(id=20, name=name, description=description, is_system=is_system, permissions=permissions)
        return roles[20]

    monkeypatch.setattr(RoleRepository, "list_roles", lambda self: sorted(roles.values(), key=lambda r: r.name))
    monkeypatch.setattr(RoleRepository, "user_counts", lambda self: state.counts)
    monkeypatch.setattr(RoleRepository, "count_users", lambda self, role_id: state.counts.get(role_id, 0))
    monkeypatch.setattr(RoleRepository, "list_permissions", lambda self: sorted(catalog.values(), key=lambda p: p.code))
    monkeypatch.setattr(RoleRepository, "get_permissions", lambda self, codes: [catalog[c] for c in sorted(codes)])
    monkeypatch.setattr(RoleRepository, "get_for_update", lambda self, role_id: roles.get(role_id))
    monkeypatch.setattr(RoleRepository, "create", create)
    monkeypatch.setattr(RoleRepository, "delete", lambda self, r: state.deleted.append(r.id))
    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: state.audit.append(entry))
    app.dependency_overrides[get_db] = lambda: state.session
    yield state
    app.dependency_overrides.clear()


def as_user(user) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_moderator_reads_roles_and_permissions(world):
    client = as_user(MODERATOR)
    permissions = client.get("/admin/permissions").json()
    assert {"code": "audit:read", "description": "Read the audit log"} in permissions
    roles = {r["name"]: r for r in client.get("/admin/roles").json()}
    assert list(roles) == ["admin", "catalog_editor", "moderator", "user"]
    assert roles["catalog_editor"] == {
        "id": 10,
        "name": "catalog_editor",
        "description": "",
        "is_system": False,
        "permissions": ["skill:update_any"],
        "users_count": 0,
    }
    assert roles["user"]["users_count"] == 5 and roles["user"]["is_system"] is True


def test_plain_user_cannot_read_roles(world):
    assert as_user(actor("user", 4)).get("/admin/roles").status_code == 403
    assert as_user(actor("user", 4)).get("/admin/permissions").status_code == 403


def test_admin_creates_a_role_and_it_is_audited(world):
    body = {"name": "auditor", "description": "Reads the log", "permissions": ["audit:read", "user:list_read"]}
    response = as_user(ADMIN).post("/admin/roles", json=body)
    assert response.status_code == 201
    assert response.json() == {**body, "id": 20, "is_system": False, "users_count": 0}
    [entry] = world.audit
    assert (entry.actor_user_id, entry.action, entry.entity_type, entry.entity_id) == (1, "role.create", "role", 20)
    assert entry.changes == {"name": "auditor", "description": "Reads the log", "permissions": ["audit:read", "user:list_read"]}
    assert world.session.commits == 1


def test_moderator_cannot_create_roles(world):
    response = as_user(MODERATOR).post("/admin/roles", json={"name": "x_role"})
    assert response.status_code == 403 and response.json() == {"detail": "Missing permission: role:manage"}


def test_role_manager_cannot_grant_what_they_lack(world):
    response = as_user(ROLE_MANAGER).post("/admin/roles", json={"name": "auditor", "permissions": ["audit:read"]})
    assert response.status_code == 403 and "audit:read" in response.json()["detail"]
    assert world.audit == []


@pytest.mark.parametrize(
    "body",
    [
        {"name": "Auditor"},
        {"name": "a"},
        {"name": "has space"},
        {"name": "auditor", "permissions": ["root:everything"]},
        {"name": "auditor", "description": "x" * 256},
    ],
)
def test_invalid_payload_is_422(world, body):
    assert as_user(ADMIN).post("/admin/roles", json=body).status_code == 422


def test_duplicate_name_is_409(world):
    response = as_user(ADMIN).post("/admin/roles", json={"name": "moderator"})
    assert response.status_code == 409 and response.json() == {"detail": "A role with that name already exists"}


def test_admin_edits_a_system_role_and_the_diff_is_audited(world):
    response = as_user(ADMIN).patch("/admin/roles/2", json={"permissions": ["skill:update_any", "audit:read"]})
    assert response.status_code == 200
    assert response.json()["permissions"] == ["audit:read", "skill:update_any"]
    [entry] = world.audit
    assert entry.action == "role.update"
    assert entry.changes == {
        "permissions": {
            "added": ["audit:read"],
            "removed": ["company:delete", "company:update_any", "industry:manage", "role:read", "user:list_read"],
        }
    }


def test_role_manager_cannot_edit_system_roles(world):
    response = as_user(ROLE_MANAGER).patch("/admin/roles/1", json={"description": "x"})
    assert response.status_code == 403 and response.json() == {"detail": "Only an admin can edit a system role"}


@pytest.mark.parametrize(("role_id", "body"), [(3, {"description": "x"}), (2, {"name": "mods"})])
def test_admin_role_and_system_names_are_fixed(world, role_id, body):
    assert as_user(ADMIN).patch(f"/admin/roles/{role_id}", json=body).status_code == 409


def test_role_manager_renames_a_custom_role(world):
    response = as_user(ROLE_MANAGER).patch("/admin/roles/10", json={"name": "skill_editor", "permissions": ["skill:update_any", "industry:manage"]})
    assert response.status_code == 200 and response.json()["name"] == "skill_editor"
    [entry] = world.audit
    assert entry.changes == {
        "name": {"before": "catalog_editor", "after": "skill_editor"},
        "permissions": {"added": ["industry:manage"]},
    }


def test_noop_edit_is_not_audited(world):
    response = as_user(ADMIN).patch("/admin/roles/10", json={"name": "catalog_editor", "permissions": ["skill:update_any"]})
    assert response.status_code == 200 and world.audit == []
    assert world.session.commits == 1  # still commits, releasing the row lock


def test_unknown_role_is_404(world):
    assert as_user(ADMIN).patch("/admin/roles/99", json={"description": "x"}).status_code == 404
    assert as_user(ADMIN).delete("/admin/roles/99").status_code == 404


def test_admin_deletes_an_unused_custom_role(world):
    assert as_user(ADMIN).delete("/admin/roles/10").status_code == 204
    assert world.deleted == [10]
    [entry] = world.audit
    assert entry.action == "role.delete"
    assert entry.changes == {"name": "catalog_editor", "description": "", "permissions": ["skill:update_any"]}


def test_role_in_use_or_system_is_not_deleted(world):
    world.counts[10] = 2
    assert as_user(ADMIN).delete("/admin/roles/10").status_code == 409
    assert as_user(ADMIN).delete("/admin/roles/1").status_code == 409
    assert world.deleted == [] and world.audit == []


def test_assignment_racing_the_delete_is_409(world):
    world.session.fail_commit = IntegrityError("DELETE", {}, Exception("fk"))
    response = as_user(ADMIN).delete("/admin/roles/10")
    assert response.status_code == 409 and "assigned" in response.json()["detail"]


def test_rename_to_a_name_taken_meanwhile_is_409(world):
    world.session.fail_commit = IntegrityError("UPDATE", {}, Exception("duplicate"))
    response = as_user(ADMIN).patch("/admin/roles/10", json={"name": "taken", "permissions": ["audit:read"]})
    assert response.status_code == 409 and response.json() == {"detail": "A role with that name already exists"}
