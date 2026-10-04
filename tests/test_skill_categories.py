import json
from types import SimpleNamespace

import pytest
from factories import FakeSession

from aptum.common.enums import SkillCategory
from aptum.modules.profile.models import ProfileSkill
from aptum.modules.profile.schemas import ProfileSkillCreate, ProfileSkillUpdate
from aptum.modules.profile.service import ProfileService
from aptum.modules.skills.categories import (
    DICTIONARY_PATH,
    classify_skill,
    get_dictionary,
    load_dictionary,
)


@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("OpenAI API", SkillCategory.llms_ai),
        ("openai", SkillCategory.llms_ai),
        ("RAG", SkillCategory.llms_ai),
        ("Retrieval-Augmented Generation", SkillCategory.llms_ai),
        ("FastAPI", SkillCategory.backend),
        ("fast api", SkillCategory.backend),
        ("NodeJS", SkillCategory.backend),
        ("Node.js", SkillCategory.backend),
        ("Docker", SkillCategory.cloud_devops),
        ("  DOCKER  ", SkillCategory.cloud_devops),
        ("CI/CD", SkillCategory.cloud_devops),
        ("Swift", SkillCategory.mobile),
        ("swiftui", SkillCategory.mobile),
        ("Hexagonal Architecture", SkillCategory.architecture),
        ("ports-and-adapters", SkillCategory.architecture),
        ("Pinecone", SkillCategory.llms_ai),
        ("Cobol", SkillCategory.other),
        ("Excel", SkillCategory.other),
        ("", SkillCategory.other),
    ],
)
def test_classify_is_case_insensitive_with_aliases(name, category):
    assert classify_skill(name) is category


def test_dictionary_is_versioned_and_valid():
    raw = json.loads(DICTIONARY_PATH.read_text())
    assert isinstance(raw["version"], int) and raw["version"] >= 1
    assert set(raw["categories"]) <= {c.value for c in SkillCategory}
    assert get_dictionary().version == raw["version"]


def test_dictionary_rejects_duplicate_terms(tmp_path):
    path = tmp_path / "dict.json"
    path.write_text(json.dumps({
        "version": 1,
        "categories": {"Backend": [{"name": "Docker"}], "Cloud & DevOps": [{"name": "docker"}]},
    }))
    with pytest.raises(ValueError, match="listed twice"):
        load_dictionary(path)


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
        return SimpleNamespace(skill=SimpleNamespace(name="LangChain"))

    def update_row(self, row, **fields):
        self.saved = fields
        return fields


def _service(skill_name: str) -> ProfileService:
    service = ProfileService.__new__(ProfileService)
    service.db = FakeSession()
    service.repository = _FakeRepo(SimpleNamespace(skills=[], languages=[]))
    service.skills = SimpleNamespace(get=lambda skill_id: SimpleNamespace(id=skill_id, name=skill_name))
    return service


def test_api_classifies_new_skill_unless_category_is_sent():
    service = _service("FastAPI")
    service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=7))
    assert service.repository.saved["category"] == "Backend"

    service.add_row(1, ProfileSkill, ProfileSkillCreate(skill_id=7, category="Architecture"))
    assert service.repository.saved["category"] == "Architecture"


def test_api_update_null_category_reclassifies_and_omitted_keeps():
    service = _service("unused")
    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(category=None))
    assert service.repository.saved["category"] == "LLMs & AI"

    service.update_row(1, ProfileSkill, 3, ProfileSkillUpdate(years_experience=2))
    assert "category" not in service.repository.saved


def test_api_rejects_unknown_category():
    with pytest.raises(ValueError):
        ProfileSkillCreate(skill_id=1, category="Frontend")
