"""Multi-account web support: the expected-account header and signing out everywhere."""

import pytest
from factories import FakeSession, actor
from fastapi.testclient import TestClient

from aptum.core import dependencies
from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.users import service as user_service
from aptum.modules.users.service import UserService

AUTH = {"Authorization": "Bearer token"}


@pytest.fixture
def token_for(monkeypatch):
    app.dependency_overrides[get_db] = FakeSession

    def factory(user_id: int) -> TestClient:
        monkeypatch.setattr(
            dependencies,
            "verify_id_token",
            lambda token: {"uid": f"fb-{user_id}", "email": f"u{user_id}@example.com", "email_verified": True},
        )
        monkeypatch.setattr(UserService, "get_or_create_from_firebase", lambda self, uid, email: actor("user", user_id))
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()


def test_no_expected_account_keeps_the_current_behaviour(token_for):
    response = token_for(7).get("/users/me", headers=AUTH)
    assert response.status_code == 200 and response.json()["id"] == 7


def test_matching_expected_account_passes(token_for):
    response = token_for(7).get("/users/me", headers={**AUTH, "X-Aptum-Account": "7"})
    assert response.status_code == 200


@pytest.mark.parametrize("expected", ["8", "", "abc", "7 8"])
def test_a_token_for_another_account_is_refused(token_for, expected):
    response = token_for(7).get("/users/me", headers={**AUTH, "X-Aptum-Account": expected})
    assert response.status_code == 409
    assert response.json() == {"detail": "Account mismatch"}


def test_mismatch_blocks_writes_before_they_reach_the_service(token_for, monkeypatch):
    called = []
    monkeypatch.setattr(UserService, "revoke_sessions", lambda self, user: called.append(user))
    response = token_for(7).post("/users/me/sessions/revoke", headers={**AUTH, "X-Aptum-Account": "8"})
    assert response.status_code == 409 and called == []


def test_the_header_is_not_part_of_the_openapi_schema():
    schema = TestClient(app).get("/openapi.json").json()
    params = schema["paths"]["/users/me"]["get"].get("parameters", [])
    assert all(param["name"].lower() != "x-aptum-account" for param in params)


@pytest.fixture
def signed_in(monkeypatch):
    revoked, entries = [], []
    session = FakeSession()
    monkeypatch.setattr(user_service, "revoke_refresh_tokens", revoked.append)
    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: entries.append(entry))
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: actor("user", 4, firebase_uid="fb-4")
    yield TestClient(app), revoked, entries, session
    app.dependency_overrides.clear()


def test_revoke_signs_the_caller_out_everywhere_and_audits_it(signed_in):
    client, revoked, entries, session = signed_in
    response = client.post("/users/me/sessions/revoke")
    assert response.status_code == 204
    assert revoked == ["fb-4"]
    [entry] = entries
    assert (entry.actor_user_id, entry.action, entry.entity_type, entry.entity_id) == (4, "user.sessions_revoke", "user", 4)
    assert entry.changes == {}
    assert session.commits == 1


def test_revoke_failure_writes_no_audit_entry(signed_in, monkeypatch):
    _, _, entries, session = signed_in

    def fail(uid):
        raise RuntimeError("firebase down")

    monkeypatch.setattr(user_service, "revoke_refresh_tokens", fail)
    response = TestClient(app, raise_server_exceptions=False).post("/users/me/sessions/revoke")
    assert response.status_code == 500
    assert entries == [] and session.commits == 0
