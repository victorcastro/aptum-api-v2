from types import SimpleNamespace

import pytest
from factories import FakeSession, base_profile
from pydantic import ValidationError

from aptum.core.exceptions import NotFoundError
from aptum.modules.profile.schemas import (
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
)
from aptum.modules.profile.service import ProfileService

CATALOG = {1: "Python", 2: "FastAPI", 3: "Docker"}


class _FakeRepo:
    def __init__(self):
        self.added: dict = {}
        self.updated: dict = {}

    def get_by_user_id(self, user_id):
        return SimpleNamespace(id=1)

    def add_experience(self, profile, functions, skills, **fields):
        self.added = {"functions": functions, "skills": skills, **fields}
        return self.added

    def update_experience(self, experience, functions, skills, **fields):
        self.updated = {"functions": functions, "skills": skills, **fields}
        return self.updated

    def get_row(self, model, profile, row_id):
        return SimpleNamespace(
            start_date="2020-01", end_date=None, employer_id=1, client_id=None
        )


def _service() -> ProfileService:
    service = ProfileService.__new__(ProfileService)
    service.db = FakeSession()
    service.repository = _FakeRepo()
    service.companies = SimpleNamespace(get=lambda company_id: SimpleNamespace(id=company_id))
    service.skills = SimpleNamespace(
        get=lambda skill_id: SimpleNamespace(id=skill_id, name=CATALOG[skill_id]) if skill_id in CATALOG else None
    )
    return service


def _create(**fields) -> ExperienceCreate:
    return ExperienceCreate(position="Engineer", employer_id=1, start_date="2020-01", **fields)


def test_create_keeps_the_skills_in_the_order_sent_without_repeats():
    service = _service()
    service.add_experience(1, _create(skill_ids=[3, 1, 3, 2]))
    assert [skill.name for skill in service.repository.added["skills"]] == ["Docker", "Python", "FastAPI"]
    assert "skill_ids" not in service.repository.added


def test_create_without_skill_ids_saves_no_skills():
    service = _service()
    service.add_experience(1, _create())
    assert service.repository.added["skills"] == []


def test_unknown_skill_is_404():
    with pytest.raises(NotFoundError, match="Skill not found"):
        _service().add_experience(1, _create(skill_ids=[1, 99]))


def test_update_replaces_skills_only_when_sent():
    service = _service()
    service.update_experience(1, 5, ExperienceUpdate(position="Lead"))
    assert service.repository.updated["skills"] is None
    service.update_experience(1, 5, ExperienceUpdate(skill_ids=[2]))
    assert [skill.name for skill in service.repository.updated["skills"]] == ["FastAPI"]
    service.update_experience(1, 5, ExperienceUpdate(skill_ids=[]))
    assert service.repository.updated["skills"] == []


def test_update_rejects_null_skill_ids():
    with pytest.raises(ValidationError):
        ExperienceUpdate(skill_ids=None)


def test_read_lists_the_skills_of_the_experience():
    experience = next(exp for exp in base_profile().experiences if exp.skills)
    for index, row in enumerate([*experience.functions, *experience.skills, experience, experience.employer], start=1):
        row.id = index
    read = ExperienceRead.model_validate(experience)
    assert [skill.name for skill in read.skills] == [skill.name for skill in experience.skills]
