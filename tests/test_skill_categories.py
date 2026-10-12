import json
from types import SimpleNamespace

import pytest
from factories import FakeSession

from aptum.core.exceptions import AptumError, NotFoundError
from aptum.modules.profile.models import ProfileSkill
from aptum.modules.profile.schemas import (
    ProfileSkillCreate,
    ProfileSkillOrder,
    ProfileSkillUpdate,
)
from aptum.modules.profile.service import ProfileService
from aptum.modules.skills.categories import (
    DICTIONARY_PATH,
    get_dictionary,
    load_dictionary,
    lookup,
    skill_terms,
)


def test_lookup_is_case_insensitive_and_follows_aliases():
    assert lookup("openai").name == "OpenAI API"
    assert lookup("  DOCKER  ").name == "Docker"
    assert lookup("fast api").name == "FastAPI"
    assert lookup("Cobol") is None
    assert lookup("") is None


def test_skill_terms_adds_the_aliases_of_known_skills():
    assert "openai" in skill_terms("OpenAI API")
    assert skill_terms("Cobol") == ("Cobol",)


def test_dictionary_is_versioned():
    raw = json.loads(DICTIONARY_PATH.read_text())
    assert isinstance(raw["version"], int) and raw["version"] >= 1
    assert get_dictionary().version == raw["version"]


def test_dictionary_rejects_duplicate_terms(tmp_path):
    path = tmp_path / "dict.json"
    path.write_text(json.dumps({
        "version": 1,
        "categories": {"Backend": [{"name": "Docker"}], "Cloud & DevOps": [{"name": "docker"}]},
    }))
    with pytest.raises(ValueError, match="listed twice"):
        load_dictionary(path)


MY_PROFILE = 1
OTHER_PROFILE = 2


class _FakeRepo:
    def __init__(self, profile):
        self.profile = profile
        self.saved: dict = {}

    def get_by_user_id(self, user_id):
        return self.profile

    def add_row(self, model, profile, **fields):
        self.saved = fields
        return fields

    def get_row(self, model, profile, row_id):
        return SimpleNamespace(profile_id=profile.id, category_id=None, skill=SimpleNamespace(name="LangChain"))

    def update_row(self, row, **fields):
        self.saved = fields
        return fields


def _service() -> ProfileService:
    service = ProfileService.__new__(ProfileService)
    service.db = FakeSession()
    service.repository = _FakeRepo(SimpleNamespace(id=MY_PROFILE, skills=[], languages=[]))
    service.skills = SimpleNamespace(get=lambda skill_id: SimpleNamespace(id=skill_id, name="FastAPI"))
    owners = {2: MY_PROFILE, 4: MY_PROFILE, 8: OTHER_PROFILE}
    service.categories = SimpleNamespace(
        get_owned=lambda profile_id, category_id: (
            SimpleNamespace(id=category_id) if owners.get(category_id) == profile_id else None
        )
    )
    return service


def test_new_skill_without_category_goes_to_other():
    service = _service()
    service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=7))
    assert service.repository.saved["category_id"] is None


def test_new_skill_keeps_the_category_sent():
    service = _service()
    service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=7, category_id=4))
    assert service.repository.saved["category_id"] == 4


@pytest.mark.parametrize("category_id", [99, 8])
def test_unknown_or_another_users_category_is_404_on_create_and_update(category_id):
    service = _service()
    with pytest.raises(NotFoundError, match="Skill category not found"):
        service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=7, category_id=category_id))
    with pytest.raises(NotFoundError, match="Skill category not found"):
        service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(category_id=category_id))


def test_update_null_category_moves_to_other_and_omitted_keeps():
    service = _service()
    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(category_id=None))
    assert service.repository.saved["category_id"] is None

    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate())
    assert "category_id" not in service.repository.saved


def test_new_skill_goes_to_the_end_of_its_category():
    service = _service()
    service.repository.profile.skills = [
        SimpleNamespace(skill_id=1, category_id=4, position=3),
        SimpleNamespace(skill_id=2, category_id=4, position=1),
        SimpleNamespace(skill_id=3, category_id=None, position=9),
    ]
    service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=7, category_id=4))
    assert service.repository.saved["position"] == 4
    service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=8, category_id=2))
    assert service.repository.saved["position"] == 1


def test_moving_to_another_category_goes_to_its_end_and_same_category_keeps_position():
    service = _service()
    service.repository.profile.skills = [SimpleNamespace(category_id=4, position=2)]
    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(category_id=4))
    assert service.repository.saved["position"] == 3

    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(category_id=None))
    assert "position" not in service.repository.saved


def _skills(*items):
    return [SimpleNamespace(id=i, category_id=c, position=0) for i, c in items]


def test_reorder_skills_numbers_the_category_from_one():
    service = _service()
    rows = _skills((1, 4), (2, 4), (3, 4), (4, None))
    service.repository.profile.skills = rows
    service.list_skills_grouped = lambda user_id: "grouped"

    assert service.reorder_skills(1, ProfileSkillOrder(category_id=4, ids=[3, 1, 2])) == "grouped"
    assert [row.position for row in rows] == [2, 3, 1, 0]


@pytest.mark.parametrize("ids", [[1, 2], [1, 2, 3, 3], [1, 2, 9], [1, 2, 4]])
def test_reorder_skills_needs_every_skill_of_the_category_once(ids):
    service = _service()
    service.repository.profile.skills = _skills((1, 4), (2, 4), (3, 4), (4, None))
    with pytest.raises(AptumError, match="every skill of the category"):
        service.reorder_skills(1, ProfileSkillOrder(category_id=4, ids=ids))


def test_reorder_skills_of_an_unknown_category_is_404():
    service = _service()
    with pytest.raises(NotFoundError, match="Skill category not found"):
        service.reorder_skills(1, ProfileSkillOrder(category_id=8, ids=[1]))
