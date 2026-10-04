"""Moderation of the shared catalogs (skills, industries, company merge/delete). Stubbed repositories."""

from types import SimpleNamespace

import pytest
from factories import FakeSession, actor
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.companies.models import Company, Industry
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.skills.models import Skill
from aptum.modules.skills.repository import SkillRepository


@pytest.fixture
def state(monkeypatch):
    state = SimpleNamespace(audit=[], session=FakeSession())
    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: state.audit.append(entry))
    app.dependency_overrides[get_db] = lambda: state.session
    yield state
    app.dependency_overrides.clear()


def as_role(role: str) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: actor(role, 7)
    return TestClient(app)


# --- skills ------------------------------------------------------------------------------------


@pytest.fixture
def skills(monkeypatch):
    rows = {1: Skill(id=1, name="React", slug="react"), 2: Skill(id=2, name="ReactJS", slug="reactjs")}
    monkeypatch.setattr(SkillRepository, "get", lambda self, skill_id: rows.get(skill_id))
    monkeypatch.setattr(
        SkillRepository, "get_by_slug", lambda self, slug: next((s for s in rows.values() if s.slug == slug), None)
    )

    def update(self, skill, **fields):
        for key, value in fields.items():
            setattr(skill, key, value)
        return skill

    monkeypatch.setattr(SkillRepository, "update", update)
    return rows


def test_any_user_lists_the_skill_catalog_without_a_query(state, monkeypatch):
    pages = []
    rows = [Skill(id=1, name="React", slug="react")]
    monkeypatch.setattr(SkillRepository, "list_page", lambda self, limit, offset: pages.append((limit, offset)) or rows)
    response = as_role("user").get("/skills", params={"offset": 100})
    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "React", "slug": "react"}]
    assert pages == [(100, 100)]


def test_moderator_renames_a_skill_and_slug_follows(state, skills):
    response = as_role("moderator").patch("/skills/2", json={"name": " React Native "})
    assert response.status_code == 200
    assert response.json() == {"id": 2, "name": "React Native", "slug": "react-native"}
    [entry] = state.audit
    assert entry.action == "skill.update"
    assert entry.changes == {
        "name": {"before": "ReactJS", "after": "React Native"},
        "slug": {"before": "reactjs", "after": "react-native"},
    }


@pytest.mark.parametrize("name", ["react", "REACT", "Réact"])
def test_skill_rename_clashing_with_another_normalized_name_is_409(state, skills, name):
    response = as_role("moderator").patch("/skills/2", json={"name": name})
    assert response.status_code == 409
    assert state.audit == []


def test_skill_rename_to_its_own_name_in_other_case_is_allowed(state, skills):
    assert as_role("moderator").patch("/skills/1", json={"name": "REACT"}).status_code == 200


def test_skill_rename_commits_once_with_its_audit_entry(state, skills):
    as_role("moderator").patch("/skills/2", json={"name": "Vue"})
    assert state.session.commits == 1 and len(state.audit) == 1


def test_concurrent_skill_rename_to_the_same_slug_is_409(state, skills):
    state.session.fail_commit = IntegrityError("UPDATE skills", {}, Exception("unique"))
    assert as_role("moderator").patch("/skills/2", json={"name": "Vue"}).status_code == 409
    assert state.session.rollbacks == 1


@pytest.mark.parametrize(
    ("body", "status"), [({"name": "!!!"}, 400), ({"name": None}, 422), ({}, 422), ({"category": "Backend"}, 422)]
)
def test_skill_rename_validation(state, skills, body, status):
    assert as_role("moderator").patch("/skills/1", json=body).status_code == status


def test_unknown_skill_is_404(state, skills):
    assert as_role("moderator").patch("/skills/99", json={"name": "Vue"}).status_code == 404


def test_users_cannot_moderate_skills(state, skills):
    assert as_role("user").patch("/skills/1", json={"name": "Vue"}).status_code == 403


# --- industries --------------------------------------------------------------------------------


@pytest.fixture
def industries(monkeypatch):
    rows = [Industry(id=1, name="Banking", slug="banking"), Industry(id=2, name="Information Technology and Services", slug="information-technology-services")]
    monkeypatch.setattr(CompanyRepository, "list_industries", lambda self: rows)
    monkeypatch.setattr(CompanyRepository, "get_industry", lambda self, i: next((r for r in rows if r.id == i), None))

    def create_industry(self, name, slug):
        industry = Industry(id=50, name=name, slug=slug)
        rows.append(industry)
        return industry

    monkeypatch.setattr(CompanyRepository, "create_industry", create_industry)
    return rows


def test_moderator_creates_an_industry(state, industries):
    response = as_role("moderator").post("/companies/industries", json={"name": "Quantum Computing"})
    assert response.status_code == 201
    assert response.json() == {"id": 50, "name": "Quantum Computing", "slug": "quantum-computing"}
    assert state.audit[0].action == "industry.create" and state.session.commits == 1


@pytest.mark.parametrize("name", ["banking", "  BANKING ", "information technology and services"])
def test_industry_name_clash_is_409(state, industries, name):
    assert as_role("moderator").post("/companies/industries", json={"name": name}).status_code == 409
    assert state.audit == []


def test_industry_rename_is_audited(state, industries):
    response = as_role("admin").patch("/companies/industries/1", json={"name": "Banking & Finance"})
    assert response.json() == {"id": 1, "name": "Banking & Finance", "slug": "banking-finance"}
    assert state.audit[0].changes["name"] == {"before": "Banking", "after": "Banking & Finance"}


def test_industry_rename_to_same_name_is_a_noop(state, industries):
    assert as_role("admin").patch("/companies/industries/1", json={"name": "Banking"}).status_code == 200
    assert state.audit == [] and state.session.commits == 0


def test_users_cannot_manage_industries(state, industries):
    assert as_role("user").post("/companies/industries", json={"name": "Retail"}).status_code == 403
    assert as_role("user").patch("/companies/industries/1", json={"name": "Retail"}).status_code == 403


# --- company merge / delete --------------------------------------------------------------------


@pytest.fixture
def companies(monkeypatch):
    rows = {
        1: Company(id=1, name="NTT Data", normalized_name="ntt data", is_consultancy=True),
        2: Company(id=2, name="NTT DATA SA", normalized_name="ntt data sa", is_consultancy=True),
        3: Company(id=3, name="Unused", normalized_name="unused", is_consultancy=False),
    }
    deleted = []
    monkeypatch.setattr(CompanyRepository, "get", lambda self, i: rows.get(i))
    monkeypatch.setattr(CompanyRepository, "lock_pair", lambda self, a, b: {i: rows[i] for i in (a, b) if i in rows})
    monkeypatch.setattr(
        CompanyRepository,
        "repoint_experiences",
        lambda self, source, target: {"employer": 2, "client": 1, "client_cleared": 1},
    )
    monkeypatch.setattr(CompanyRepository, "used_ids", lambda self, ids: {i for i in ids if i in (1, 2)})
    monkeypatch.setattr(CompanyRepository, "delete", lambda self, company: deleted.append(company.id))
    return deleted


def test_admin_merges_a_duplicate(state, companies):
    response = as_role("admin").post("/companies/2/merge", json={"target_id": 1})
    assert response.status_code == 200 and response.json()["id"] == 1 and response.json()["can_edit"] is True
    assert companies == [2] and state.session.commits == 1
    [entry] = state.audit
    assert (entry.action, entry.entity_id) == ("company.merge", 2)
    assert entry.changes["merged_into"] == 1
    assert entry.changes["experiences"] == {"employer": 2, "client": 1, "client_cleared": 1}
    assert entry.changes["deleted"]["name"] == "NTT DATA SA"


@pytest.mark.parametrize(("path", "body", "status"), [("/companies/1/merge", {"target_id": 1}, 409), ("/companies/2/merge", {"target_id": 99}, 404)])
def test_merge_errors(state, companies, path, body, status):
    assert as_role("admin").post(path, json=body).status_code == status
    assert companies == [] and state.audit == []


def test_moderator_cannot_merge(state, companies):
    assert as_role("moderator").post("/companies/2/merge", json={"target_id": 1}).status_code == 403


def test_moderator_deletes_an_unused_company(state, companies):
    response = as_role("moderator").delete("/companies/3")
    assert response.status_code == 204 and response.content == b""
    assert companies == [3] and state.audit[0].action == "company.delete"


def test_deleting_a_used_company_is_409(state, companies):
    response = as_role("admin").delete("/companies/1")
    assert response.status_code == 409 and "merge it instead" in response.json()["detail"]
    assert companies == [] and state.audit == []


def test_users_cannot_delete_companies(state, companies):
    assert as_role("user").delete("/companies/3").status_code == 403


# --- races on the unique names -----------------------------------------------------------------


def _unique_violation() -> IntegrityError:
    return IntegrityError("INSERT/UPDATE", {}, Exception("duplicate key"))


def test_concurrent_company_rename_to_the_same_name_is_409(state, companies, monkeypatch):
    monkeypatch.setattr(CompanyRepository, "get_by_normalized_name", lambda self, name: None)
    state.session.fail_commit = _unique_violation()
    response = as_role("admin").patch("/companies/3", json={"name": "Contoso"})
    assert response.status_code == 409 and state.session.rollbacks == 1


def test_company_created_meanwhile_by_someone_else_is_returned(state, monkeypatch):
    theirs = Company(id=8, name="Contoso", normalized_name="contoso", is_consultancy=False)
    lookups = iter([None, theirs])  # absent on the first check, present after the rollback
    monkeypatch.setattr(CompanyRepository, "get_by_normalized_name", lambda self, name: next(lookups))
    monkeypatch.setattr(CompanyRepository, "create", lambda self, **fields: Company(**fields))
    monkeypatch.setattr(CompanyRepository, "used_ids", lambda self, ids: set())
    state.session.fail_commit = _unique_violation()
    response = as_role("user").post("/companies", json={"name": "Contoso", "is_consultancy": False})
    assert response.status_code == 201 and response.json()["id"] == 8
    assert state.session.rollbacks == 1


def test_skill_created_meanwhile_by_someone_else_is_returned(state, monkeypatch):
    theirs = Skill(id=9, name="Vue", slug="vue")
    lookups = iter([None, theirs])
    monkeypatch.setattr(SkillRepository, "get_by_slug", lambda self, slug: next(lookups))
    monkeypatch.setattr(SkillRepository, "create", lambda self, **fields: Skill(**fields))
    state.session.fail_commit = _unique_violation()
    response = as_role("user").post("/skills", json={"name": "Vue"})
    assert response.status_code == 201 and response.json()["id"] == 9
    assert state.session.rollbacks == 1
