"""Each user's own skill categories under /profile/me. Stubbed repositories, in-memory rows."""

from types import SimpleNamespace

import pytest
from factories import FakeSession, actor
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.skill_categories.models import SkillCategory
from aptum.modules.skill_categories.repository import SkillCategoryRepository

ANA, BRUNO, NO_PROFILE = 7, 8, 9
PROFILES = {ANA: 70, BRUNO: 80}
URL = "/profile/me/skill-categories"


@pytest.fixture
def world(monkeypatch):
    rows = {
        1: SkillCategory(id=1, profile_id=70, name="Backend", position=1),
        2: SkillCategory(id=2, profile_id=70, name="Mobile", position=2),
        3: SkillCategory(id=3, profile_id=70, name="Data", position=3),
        4: SkillCategory(id=4, profile_id=80, name="Backend", position=1),
    }
    state = SimpleNamespace(session=FakeSession(), rows=rows, deleted=[])

    def list_for(self, profile_id):
        return sorted((c for c in rows.values() if c.profile_id == profile_id), key=lambda c: (c.position, c.id))

    def get_owned(self, profile_id, category_id):
        category = rows.get(category_id)
        return category if category is not None and category.profile_id == profile_id else None

    def next_position(self, profile_id):
        return max((c.position for c in list_for(self, profile_id)), default=0) + 1

    def create(self, profile_id, name, position):
        category = SkillCategory(id=max(rows) + 1, profile_id=profile_id, name=name, position=position)
        rows[category.id] = category
        return category

    def delete(self, category):
        state.deleted.append(category.id)
        del rows[category.id]

    monkeypatch.setattr(
        ProfileRepository,
        "get_by_user_id",
        lambda self, user_id: SimpleNamespace(id=PROFILES[user_id]) if user_id in PROFILES else None,
    )
    monkeypatch.setattr(SkillCategoryRepository, "list_for", list_for)
    monkeypatch.setattr(SkillCategoryRepository, "get_owned", get_owned)
    monkeypatch.setattr(SkillCategoryRepository, "next_position", next_position)
    monkeypatch.setattr(SkillCategoryRepository, "create", create)
    monkeypatch.setattr(SkillCategoryRepository, "delete", delete)
    app.dependency_overrides[get_db] = lambda: state.session
    yield state
    app.dependency_overrides.clear()


def as_user(user_id: int, role: str = "user") -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: actor(role, user_id)
    return TestClient(app)


def test_a_user_lists_only_their_own_categories_in_print_order(world):
    world.rows[3].position = 0
    response = as_user(ANA).get(URL)
    assert response.status_code == 200
    assert response.json() == [
        {"id": 3, "name": "Data", "position": 0},
        {"id": 1, "name": "Backend", "position": 1},
        {"id": 2, "name": "Mobile", "position": 2},
    ]
    assert [c["id"] for c in as_user(BRUNO).get(URL).json()] == [4]


def test_without_a_profile_the_list_is_empty_and_writes_are_404(world):
    client = as_user(NO_PROFILE)
    assert client.get(URL).json() == []
    assert client.post(URL, json={"name": "Data"}).status_code == 404


def test_any_user_creates_a_category_at_the_end_of_their_order(world):
    response = as_user(BRUNO).post(URL, json={"name": "  Data  "})
    assert response.status_code == 201
    assert response.json() == {"id": 5, "name": "Data", "position": 2}
    assert world.rows[5].profile_id == 80
    assert world.session.commits == 1


def test_admin_has_no_say_over_other_users_categories(world):
    client = as_user(BRUNO, role="admin")
    assert client.patch(f"{URL}/1", json={"name": "Servers"}).status_code == 404
    assert client.delete(f"{URL}/1").status_code == 404
    assert world.rows[1].name == "Backend" and world.deleted == []


@pytest.mark.parametrize("name", ["backend", "BACKEND", " Backénd "])
def test_create_with_one_of_your_names_is_409(world, name):
    assert as_user(ANA).post(URL, json={"name": name}).status_code == 409
    assert world.session.commits == 0


def test_another_user_may_use_the_same_name(world):
    assert as_user(BRUNO).post(URL, json={"name": "Mobile"}).status_code == 201


@pytest.mark.parametrize(
    ("body", "status"), [({"name": "!!!"}, 400), ({"name": ""}, 422), ({"name": "x" * 41}, 422), ({}, 422)]
)
def test_create_validation(world, body, status):
    assert as_user(ANA).post(URL, json=body).status_code == status


def test_concurrent_create_of_the_same_name_is_409(world):
    world.session.fail_commit = IntegrityError("INSERT", {}, Exception("duplicate"))
    assert as_user(ANA).post(URL, json={"name": "Cloud"}).status_code == 409
    assert world.session.rollbacks == 1


def test_a_user_renames_their_category(world):
    response = as_user(ANA).patch(f"{URL}/1", json={"name": "Servers"})
    assert response.status_code == 200 and response.json()["name"] == "Servers"
    assert world.session.commits == 1


def test_rename_to_its_own_name_in_other_case_is_allowed(world):
    assert as_user(ANA).patch(f"{URL}/1", json={"name": "BACKEND"}).status_code == 200


def test_rename_to_the_same_name_does_nothing(world):
    assert as_user(ANA).patch(f"{URL}/1", json={"name": "Backend"}).status_code == 200
    assert world.session.commits == 0


def test_rename_clashing_with_another_of_your_categories_is_409(world):
    assert as_user(ANA).patch(f"{URL}/1", json={"name": "mobile"}).status_code == 409


@pytest.mark.parametrize("category_id", [99, 4])
def test_unknown_or_another_users_category_is_404(world, category_id):
    client = as_user(ANA)
    assert client.patch(f"{URL}/{category_id}", json={"name": "Data2"}).status_code == 404
    assert client.delete(f"{URL}/{category_id}").status_code == 404
    assert world.deleted == []


def test_reorder_sets_positions_and_returns_the_new_order(world):
    response = as_user(ANA).put(f"{URL}/order", json={"ids": [3, 1, 2]})
    assert response.status_code == 200
    assert [(c["id"], c["position"]) for c in response.json()] == [(3, 1), (1, 2), (2, 3)]
    assert world.session.commits == 1


@pytest.mark.parametrize("ids", [[1, 2], [1, 1, 2, 3], [1, 2, 3, 99], [1, 2, 3, 4]])
def test_reorder_with_missing_repeated_unknown_or_foreign_ids_is_400(world, ids):
    assert as_user(ANA).put(f"{URL}/order", json={"ids": ids}).status_code == 400
    assert world.session.commits == 0


def test_reorder_with_no_ids_is_422(world):
    assert as_user(ANA).put(f"{URL}/order", json={"ids": []}).status_code == 422


def test_delete_removes_the_category(world):
    assert as_user(ANA).delete(f"{URL}/2").status_code == 204
    assert world.deleted == [2] and world.session.commits == 1
