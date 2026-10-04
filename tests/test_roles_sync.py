"""roles.sync: the pure plan, and a full run over stubbed repositories (no database)."""

from types import SimpleNamespace

import pytest
from factories import FakeSession, role

from aptum.core.permissions import Permission
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.roles.models import PermissionRecord, Role
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.roles.service import permission_changes
from aptum.modules.roles.sync import plan_permissions, sync, wanted_permissions

ALL = {permission.value for permission in Permission}


def test_plan_creates_updates_and_deletes():
    plan = plan_permissions(
        stored={"a:read": "Read A", "b:read": "old text", "gone:x": "Gone"},
        wanted={"a:read": "Read A", "b:read": "Read B", "c:new": "New"},
    )
    assert plan.create == {"c:new": "New"}
    assert plan.update == {"b:read": "Read B"}
    assert plan.delete == ["gone:x"]


def test_plan_is_empty_when_in_sync():
    assert not plan_permissions(wanted_permissions(), wanted_permissions())


def test_permission_changes_lists_only_what_moved():
    assert permission_changes({"a", "b"}, {"b", "c"}) == {"added": ["c"], "removed": ["a"]}
    assert permission_changes({"a"}, {"a"}) == {}


class SyncSession(FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.locked = False

    def execute(self, statement, params=None):
        self.locked = "pg_advisory_xact_lock" in str(statement)

    def flush(self) -> None:
        pass


@pytest.fixture
def store(monkeypatch):
    """In-memory permissions and roles behind RoleRepository; collects audit entries."""
    state = SimpleNamespace(permissions={}, roles={}, audit=[], session=SyncSession())
    ids = iter(range(100, 1000))

    def create_permission(self, code, description):
        state.permissions[code] = PermissionRecord(id=next(ids), code=code, description=description)
        return state.permissions[code]

    def create_role(self, name, description, permissions, *, is_system=False):
        state.roles[name] = Role(id=next(ids), name=name, description=description, is_system=is_system, permissions=permissions)
        return state.roles[name]

    monkeypatch.setattr(RoleRepository, "list_permissions", lambda self: list(state.permissions.values()))
    monkeypatch.setattr(RoleRepository, "list_roles", lambda self: list(state.roles.values()))
    monkeypatch.setattr(RoleRepository, "create_permission", create_permission)
    monkeypatch.setattr(RoleRepository, "delete_permission", lambda self, p: state.permissions.pop(p.code))
    monkeypatch.setattr(RoleRepository, "create", create_role)
    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: state.audit.append(entry))
    return state


def test_first_run_creates_everything(store):
    report = sync(store.session)
    assert set(store.permissions) == ALL
    assert {name: r.is_system for name, r in store.roles.items()} == {"user": True, "moderator": True, "admin": True}
    assert store.roles["admin"].permission_codes == ALL
    assert store.roles["user"].permission_codes == frozenset()
    assert "role:read" in store.roles["moderator"].permission_codes
    assert {entry.action for entry in store.audit} == {"role.create"}
    assert all(entry.actor_user_id is None and entry.changes["via"] == "sync" for entry in store.audit)
    assert store.session.locked and store.session.commits == 1
    assert len(report) == len(ALL) + 3


def test_second_run_changes_nothing(store):
    sync(store.session)
    store.audit.clear()
    assert sync(store.session) == []
    assert store.audit == []


def test_new_permission_goes_to_admin_only_and_edited_roles_are_kept(store):
    sync(store.session)
    moderator = store.roles["moderator"]
    moderator.permissions = [store.permissions["skill:update_any"]]  # an admin trimmed it
    store.permissions.pop("audit:read")  # as if the code had just added it
    for r in store.roles.values():
        r.permissions = [p for p in r.permissions if p.code != "audit:read"]
    store.audit.clear()

    report = sync(store.session)

    assert "permission created: audit:read" in report
    assert store.roles["admin"].permission_codes == ALL
    assert moderator.permission_codes == {"skill:update_any"}  # not reset to the defaults
    [entry] = store.audit
    assert entry.action == "role.update" and entry.entity_id == store.roles["admin"].id
    assert entry.changes == {"permissions": {"added": ["audit:read"]}, "via": "sync"}


def test_permission_gone_from_the_code_is_deleted_and_taken_from_roles(store):
    sync(store.session)
    legacy = PermissionRecord(id=1, code="legacy:thing", description="Old")
    store.permissions["legacy:thing"] = legacy
    editor = role("editor", {"skill:update_any"}, is_system=False)
    editor.permissions.append(legacy)
    store.roles["editor"] = editor
    store.audit.clear()

    report = sync(store.session)

    assert "legacy:thing" not in store.permissions
    assert editor.permission_codes == {"skill:update_any"}
    assert "permission deleted: legacy:thing" in report
    changes = {entry.entity_id: entry.changes for entry in store.audit}
    assert changes[editor.id] == {"permissions": {"removed": ["legacy:thing"]}, "via": "sync"}


def test_descriptions_follow_the_code(store):
    sync(store.session)
    store.permissions["audit:read"].description = "stale"
    assert sync(store.session) == ["permission description updated: audit:read"]
    assert store.permissions["audit:read"].description == "Read the audit log"


def test_custom_role_squatting_a_system_name_stops_the_start(store):
    store.roles["moderator"] = role("moderator", set(), is_system=False)
    with pytest.raises(RuntimeError, match="not a system role"):
        sync(store.session)
    assert store.session.commits == 0
