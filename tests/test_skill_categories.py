import json
from types import SimpleNamespace

import pytest
from factories import FakeSession

from aptum.core.exceptions import NotFoundError
from aptum.modules.profile.models import ProfileSkill
from aptum.modules.profile.schemas import ProfileSkillCreate, ProfileSkillUpdate
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
        return SimpleNamespace(profile_id=profile.id, skill=SimpleNamespace(name="LangChain"))

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

    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(years_experience=2))
    assert "category_id" not in service.repository.saved
