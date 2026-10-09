"""CRUD and reorder of skill categories. Stubbed repository, in-memory rows."""

from types import SimpleNamespace

import pytest
from factories import FakeSession, actor
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from aptum.core.dependencies import get_current_user, get_db
from aptum.core.permissions import Permission
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.skill_categories.models import SkillCategory
from aptum.modules.skill_categories.repository import SkillCategoryRepository

NAMES = ["LLMs & AI", "Backend", "Cloud & DevOps", "Architecture", "Mobile", "Other"]


@pytest.fixture
def world(monkeypatch):
    rows = {
        position: SkillCategory(id=position, name=name, position=position, is_system=name == "Other")
        for position, name in enumerate(NAMES, 1)
    }
    state = SimpleNamespace(audit=[], session=FakeSession(), rows=rows, reassigned=[], deleted=[])

    def ordered(self):
        return sorted(rows.values(), key=lambda c: (c.position, c.id))

    def create(self, name, position):
        category = SkillCategory(id=max(rows) + 1, name=name, position=position, is_system=False)
        rows[category.id] = category
        return category

    def reassign(self, from_id, to_id):
        state.reassigned.append((from_id, to_id))
        return 3

    def delete(self, category):
        state.deleted.append(category.id)
        del rows[category.id]

    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: state.audit.append(entry))
    monkeypatch.setattr(SkillCategoryRepository, "list_all", ordered)
    monkeypatch.setattr(SkillCategoryRepository, "get", lambda self, category_id: rows.get(category_id))
    monkeypatch.setattr(SkillCategoryRepository, "get_other", lambda self: rows[6])
    monkeypatch.setattr(SkillCategoryRepository, "next_position", lambda self: max(c.position for c in rows.values()) + 1)
    monkeypatch.setattr(SkillCategoryRepository, "create", create)
    monkeypatch.setattr(SkillCategoryRepository, "reassign_profile_skills", reassign)
    monkeypatch.setattr(SkillCategoryRepository, "delete", delete)
    app.dependency_overrides[get_db] = lambda: state.session
    yield state
    app.dependency_overrides.clear()


def as_role(role: str, **fields) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: actor(role, 7, **fields)
    return TestClient(app)


def test_the_permission_is_admin_only_by_default():
    assert Permission.skill_category_manage == "skill_category:manage"
    assert actor("admin").permissions >= {Permission.skill_category_manage}
    assert Permission.skill_category_manage not in actor("moderator").permissions


def test_any_user_lists_categories_in_print_order(world):
    world.rows[5].position = 0
    response = as_role("user").get("/skill-categories")
    assert response.status_code == 200
    assert [c["name"] for c in response.json()] == ["Mobile", "LLMs & AI", "Backend", "Cloud & DevOps", "Architecture", "Other"]
    assert response.json()[-1] == {"id": 6, "name": "Other", "position": 6, "is_system": True}


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_without_the_permission_every_write_is_403(world, method):
    client = as_role("moderator")
    path = {"post": "/skill-categories", "put": "/skill-categories/order"}.get(method, "/skill-categories/2")
    kwargs = {} if method == "delete" else {"json": {"name": "X", "ids": [1]}}
    assert getattr(client, method)(path, **kwargs).status_code == 403
    assert world.audit == [] and world.session.commits == 0


def test_a_custom_role_with_the_permission_may_write(world):
    client = as_role("catalog_editor", permissions={"skill_category:manage"})
    assert client.post("/skill-categories", json={"name": "Data"}).status_code == 201


def test_admin_creates_a_category_at_the_end_and_it_is_audited(world):
    response = as_role("admin").post("/skill-categories", json={"name": "  Data  "})
    assert response.status_code == 201
    assert response.json() == {"id": 7, "name": "Data", "position": 7, "is_system": False}
    [entry] = world.audit
    assert entry.action == "skill_category.create" and entry.entity_type == "skill_category" and entry.entity_id == 7
    assert entry.changes["name"] == {"before": None, "after": "Data"}
    assert world.session.commits == 1


@pytest.mark.parametrize("name", ["backend", "BACKEND", " Backénd "])
def test_create_with_a_taken_normalized_name_is_409(world, name):
    assert as_role("admin").post("/skill-categories", json={"name": name}).status_code == 409
    assert world.audit == [] and world.session.commits == 0


@pytest.mark.parametrize(
    ("body", "status"), [({"name": "!!!"}, 400), ({"name": ""}, 422), ({"name": "x" * 41}, 422), ({}, 422)]
)
def test_create_validation(world, body, status):
    assert as_role("admin").post("/skill-categories", json=body).status_code == status


def test_concurrent_create_of_the_same_name_is_409(world):
    world.session.fail_commit = IntegrityError("INSERT", {}, Exception("duplicate"))
    assert as_role("admin").post("/skill-categories", json={"name": "Data"}).status_code == 409
    assert world.session.rollbacks == 1


def test_admin_renames_a_category(world):
    response = as_role("admin").patch("/skill-categories/2", json={"name": "Servers"})
    assert response.status_code == 200 and response.json()["name"] == "Servers"
    [entry] = world.audit
    assert entry.action == "skill_category.update"
    assert entry.changes == {"name": {"before": "Backend", "after": "Servers"}}


def test_rename_to_its_own_name_in_other_case_is_allowed(world):
    assert as_role("admin").patch("/skill-categories/2", json={"name": "BACKEND"}).status_code == 200


def test_rename_to_the_same_name_does_nothing(world):
    assert as_role("admin").patch("/skill-categories/2", json={"name": "Backend"}).status_code == 200
    assert world.audit == [] and world.session.commits == 0


def test_rename_clashing_with_another_category_is_409(world):
    assert as_role("admin").patch("/skill-categories/2", json={"name": "mobile"}).status_code == 409


def test_the_system_category_cannot_be_renamed(world):
    assert as_role("admin").patch("/skill-categories/6", json={"name": "Misc"}).status_code == 409
    assert world.audit == []


def test_unknown_category_is_404(world):
    client = as_role("admin")
    assert client.patch("/skill-categories/99", json={"name": "Data"}).status_code == 404
    assert client.delete("/skill-categories/99").status_code == 404


def test_reorder_sets_positions_and_audits_only_the_moved_ones(world):
    response = as_role("admin").put("/skill-categories/order", json={"ids": [2, 1, 3, 4, 5, 6]})
    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [2, 1, 3, 4, 5, 6]
    assert sorted(entry.entity_id for entry in world.audit) == [1, 2]
    assert {entry.action for entry in world.audit} == {"skill_category.reorder"}
    assert world.session.commits == 1


@pytest.mark.parametrize("ids", [[1, 2, 3], [1, 1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 9]])
def test_reorder_with_missing_repeated_or_unknown_ids_is_400(world, ids):
    assert as_role("admin").put("/skill-categories/order", json={"ids": ids}).status_code == 400
    assert world.audit == [] and world.session.commits == 0


def test_reorder_with_no_ids_is_422(world):
    assert as_role("admin").put("/skill-categories/order", json={"ids": []}).status_code == 422


def test_delete_moves_the_profile_skills_to_other_and_audits_the_count(world):
    response = as_role("admin").delete("/skill-categories/2")
    assert response.status_code == 204
    assert world.reassigned == [(2, 6)] and world.deleted == [2]
    [entry] = world.audit
    assert entry.action == "skill_category.delete"
    assert entry.changes["reassigned_count"] == 3 and entry.changes["reassigned_to"] == 6
    assert entry.changes["deleted"]["name"] == "Backend"
    assert world.session.commits == 1


def test_the_system_category_cannot_be_deleted(world):
    assert as_role("admin").delete("/skill-categories/6").status_code == 409
    assert world.reassigned == [] and world.audit == []


def test_delete_that_hits_the_foreign_key_is_409_and_rolls_back(world):
    world.session.fail_commit = IntegrityError("DELETE", {}, Exception("foreign key"))
    assert as_role("admin").delete("/skill-categories/2").status_code == 409
    assert world.session.rollbacks == 1
