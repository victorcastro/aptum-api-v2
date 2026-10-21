"""Create, edit and delete degrees. Stubbed repository: no database."""

from types import SimpleNamespace

import pytest
from factories import FakeSession, actor
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.commons.models import Degree
from aptum.modules.commons.repository import CommonsRepository


@pytest.fixture
def state(monkeypatch):
    state = SimpleNamespace(
        audit=[],
        session=FakeSession(),
        rows=[
            Degree(id=1, name="Technical Diploma", level="Technical", rank=1),
            Degree(id=2, name="Bachelor of Science", level="Undergraduate", rank=2),
            Degree(id=3, name="PhD", level="Doctoral", rank=3),
        ],
        in_use=set(),
        deleted=[],
    )

    def create(self, name, level):
        degree = Degree(id=10, name=name, level=level, rank=0)
        state.rows.append(degree)
        return degree

    def renumber(self, ordered):
        for rank, degree in enumerate(ordered, start=1):
            degree.rank = rank
        state.rows.sort(key=lambda degree: degree.rank)

    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: state.audit.append(entry))
    monkeypatch.setattr(CommonsRepository, "list_degrees", lambda self: sorted(state.rows, key=lambda d: d.rank))
    monkeypatch.setattr(CommonsRepository, "get_degree", lambda self, i: next((d for d in state.rows if d.id == i), None))
    monkeypatch.setattr(CommonsRepository, "degree_in_use", lambda self, i: i in state.in_use)
    monkeypatch.setattr(CommonsRepository, "create_degree", create)
    monkeypatch.setattr(CommonsRepository, "renumber_degrees", renumber)
    monkeypatch.setattr(CommonsRepository, "delete_degree", lambda self, d: state.deleted.append(d.id))
    app.dependency_overrides[get_db] = lambda: state.session
    yield state
    app.dependency_overrides.clear()


def as_role(role: str) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: actor(role, 7)
    return TestClient(app)


def test_moderator_creates_a_degree_at_the_end_of_its_level(state):
    response = as_role("moderator").post("/commons/degrees", json={"name": "Bachelor of Arts", "level": "undergraduate"})
    assert response.status_code == 201
    assert response.json() == {"id": 10, "name": "Bachelor of Arts", "level": "Undergraduate", "rank": 3}
    assert [d.name for d in state.rows] == ["Technical Diploma", "Bachelor of Science", "Bachelor of Arts", "PhD"]
    assert state.audit[0].action == "degree.create" and state.session.commits == 1


def test_a_new_level_goes_last(state):
    body = as_role("admin").post("/commons/degrees", json={"name": "Bootcamp", "level": "Short courses"}).json()
    assert body["rank"] == 4 and body["level"] == "Short courses"


@pytest.mark.parametrize("name", ["phd", " Ph D ".replace(" ", ""), "Bachelor  of science"])
def test_duplicate_name_is_409(state, name):
    assert as_role("moderator").post("/commons/degrees", json={"name": name, "level": "Doctoral"}).status_code == 409


def test_name_without_letters_is_400(state):
    assert as_role("moderator").post("/commons/degrees", json={"name": "--", "level": "Doctoral"}).status_code == 400


def test_concurrent_duplicate_is_409(state):
    state.session.fail_commit = IntegrityError("insert", {}, Exception())
    response = as_role("moderator").post("/commons/degrees", json={"name": "Bootcamp", "level": "Other"})
    assert response.status_code == 409 and state.session.rollbacks == 1


def test_rename_is_audited(state):
    response = as_role("moderator").patch("/commons/degrees/3", json={"name": "Doctorate"})
    assert response.status_code == 200 and response.json()["name"] == "Doctorate"
    assert state.audit[0].action == "degree.update"
    assert state.audit[0].changes == {"name": {"before": "PhD", "after": "Doctorate"}}


def test_moving_to_another_level_goes_to_its_end_and_renumbers(state):
    response = as_role("moderator").patch("/commons/degrees/3", json={"level": "Undergraduate"})
    assert response.status_code == 200
    assert response.json()["level"] == "Undergraduate" and response.json()["rank"] == 3
    assert [d.id for d in state.rows] == [1, 2, 3]
    assert state.audit[0].changes["level"] == {"before": "Doctoral", "after": "Undergraduate"}


def test_update_without_changes_is_a_noop(state):
    assert as_role("admin").patch("/commons/degrees/3", json={"name": "PhD"}).status_code == 200
    assert state.audit == [] and state.session.commits == 0


def test_rename_to_another_degrees_name_is_409(state):
    assert as_role("admin").patch("/commons/degrees/3", json={"name": "technical diploma"}).status_code == 409


def test_unknown_degree_is_404(state):
    assert as_role("admin").patch("/commons/degrees/99", json={"name": "X"}).status_code == 404
    assert as_role("admin").delete("/commons/degrees/99").status_code == 404


def test_delete_is_audited_with_a_snapshot(state):
    response = as_role("moderator").delete("/commons/degrees/3")
    assert response.status_code == 204 and state.deleted == [3]
    assert state.audit[0].action == "degree.delete"
    assert state.audit[0].changes == {"deleted": {"name": "PhD", "level": "Doctoral", "rank": 3}}


def test_delete_in_use_is_409(state):
    state.in_use.add(3)
    assert as_role("moderator").delete("/commons/degrees/3").status_code == 409
    assert state.deleted == [] and state.audit == []


def test_delete_losing_the_race_is_409(state):
    state.session.fail_commit = IntegrityError("delete", {}, Exception())
    assert as_role("moderator").delete("/commons/degrees/3").status_code == 409


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.post("/commons/degrees", json={"name": "X", "level": "Y"}),
        lambda c: c.patch("/commons/degrees/1", json={"name": "X"}),
        lambda c: c.delete("/commons/degrees/1"),
    ],
)
def test_users_cannot_manage_degrees(state, call):
    assert call(as_role("user")).status_code == 403
    assert state.audit == [] and state.session.commits == 0
