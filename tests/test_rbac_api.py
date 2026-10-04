"""What the API tells the frontend about the caller's rights. No database: repositories are stubbed."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.companies.models import Company
from aptum.modules.companies.repository import CompanyRepository


def make_user(role: str = "user", user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(id=user_id, email=f"u{user_id}@example.com", is_active=True, role=role)


@pytest.fixture
def client_as():
    app.dependency_overrides[get_db] = lambda: None

    def factory(user: SimpleNamespace) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()


def test_me_for_a_plain_user(client_as):
    body = client_as(make_user()).get("/users/me").json()
    assert body == {"id": 1, "email": "u1@example.com", "is_active": True, "role": "user", "permissions": []}


def test_me_for_a_moderator_lists_permissions_sorted(client_as):
    body = client_as(make_user("moderator")).get("/users/me").json()
    assert body["role"] == "moderator"
    assert body["permissions"] == [
        "company:delete",
        "company:update_any",
        "industry:manage",
        "skill:update_any",
        "user:list_read",
    ]


@pytest.fixture
def catalog(monkeypatch):
    """Three companies: 10 created by user 1 and unused, 11 created by user 1 and used, 12 by someone else."""
    companies = [
        Company(id=10, name="Mine Free", normalized_name="mine free", is_consultancy=False, created_by_user_id=1),
        Company(id=11, name="Mine Used", normalized_name="mine used", is_consultancy=False, created_by_user_id=1),
        Company(id=12, name="Other", normalized_name="other", is_consultancy=False, created_by_user_id=2),
    ]
    calls = []

    def used_ids(self, ids):
        calls.append(list(ids))
        return {11}

    monkeypatch.setattr(CompanyRepository, "search", lambda self, query, limit: companies)
    monkeypatch.setattr(CompanyRepository, "used_ids", used_ids)
    return calls


def test_search_computes_can_edit_with_one_in_use_query(client_as, catalog):
    body = client_as(make_user()).get("/companies", params={"q": "m"}).json()
    assert {row["id"]: row["can_edit"] for row in body} == {10: True, 11: False, 12: False}
    assert catalog == [[10, 11, 12]]  # one query for the whole page, no N+1


def test_moderator_can_edit_every_result(client_as, catalog):
    body = client_as(make_user("moderator", 9)).get("/companies", params={"q": "m"}).json()
    assert all(row["can_edit"] for row in body)
