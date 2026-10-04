"""Audit log: diff/redaction helpers, entries written by company edits, and the read endpoint."""

from types import SimpleNamespace

import pytest
from factories import FakeSession
from fastapi.testclient import TestClient

from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.audit.repository import AuditRepository
from aptum.modules.audit.service import diff, redact
from aptum.modules.companies.models import Company
from aptum.modules.companies.repository import CompanyRepository


def test_diff_keeps_changed_fields_only():
    before = {"name": "Acme", "city": "Lima", "website": None}
    after = {"name": "Acme Corp", "city": "Lima", "website": "https://acme.example"}
    assert diff(before, after) == {
        "name": {"before": "Acme", "after": "Acme Corp"},
        "website": {"before": None, "after": "https://acme.example"},
    }


def test_redact_drops_secret_keys_at_any_depth():
    changes = {"role": {"before": "user", "after": "admin"}, "firebase_uid": "x", "ctx": {"id_token": "t", "ok": 1}}
    assert redact(changes) == {"role": {"before": "user", "after": "admin"}, "ctx": {"ok": 1}}


def test_redact_looks_inside_lists():
    changes = {"items": [{"api_key": "k", "name": "a"}, "plain"], "tokens": ["t"]}
    assert redact(changes) == {"items": [{"name": "a"}, "plain"]}


@pytest.fixture
def entries(monkeypatch):
    """Stub repositories: one company created by user 1, unused. Collects audit entries."""
    company = Company(id=5, name="Acme", normalized_name="acme", is_consultancy=False, created_by_user_id=1, city="Lima")
    added = []
    monkeypatch.setattr(CompanyRepository, "get", lambda self, company_id: company if company_id == 5 else None)
    monkeypatch.setattr(CompanyRepository, "used_ids", lambda self, ids: set())
    monkeypatch.setattr(CompanyRepository, "get_by_normalized_name", lambda self, name: None)

    def update(self, target, **fields):
        for key, value in fields.items():
            setattr(target, key, value)
        return target

    monkeypatch.setattr(CompanyRepository, "update", update)
    monkeypatch.setattr(AuditRepository, "add", lambda self, entry: added.append(entry))
    return added


@pytest.fixture
def client_as():
    app.dependency_overrides[get_db] = FakeSession

    def factory(role: str = "user", user_id: int = 1) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=role)
        return TestClient(app)

    yield factory
    app.dependency_overrides.clear()


def test_company_update_writes_before_and_after_of_changed_fields(client_as, entries):
    response = client_as().patch("/companies/5", json={"name": "Acme Corp", "city": "Lima"})
    assert response.status_code == 200
    [entry] = entries
    assert (entry.actor_user_id, entry.action, entry.entity_type, entry.entity_id) == (1, "company.update", "company", 5)
    assert entry.changes == {"name": {"before": "Acme", "after": "Acme Corp"}}  # city unchanged, normalized_name derived


def test_noop_update_writes_no_entry(client_as, entries):
    assert client_as().patch("/companies/5", json={"city": "Lima"}).status_code == 200
    assert entries == []


def test_rejected_update_writes_no_entry(client_as, entries):
    assert client_as("user", 9).patch("/companies/5", json={"name": "Hijack"}).status_code == 404
    assert entries == []


def test_audit_logs_need_audit_read(client_as):
    response = client_as("moderator").get("/admin/audit-logs")
    assert response.status_code == 403
    assert response.json() == {"detail": "Missing permission: audit:read"}


def test_admin_lists_audit_logs_with_filters(client_as, monkeypatch):
    seen = {}

    def fake_list(self, **filters):
        seen.update(filters)
        return [], 0

    monkeypatch.setattr(AuditRepository, "list_page", fake_list)
    response = client_as("admin").get(
        "/admin/audit-logs", params={"entity_type": "company", "entity_id": 5, "limit": 10}
    )
    assert response.status_code == 200 and response.json() == {"items": [], "total": 0}
    assert seen["entity_type"] == "company" and seen["entity_id"] == 5
    assert (seen["limit"], seen["offset"]) == (10, 0)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"entity_type": "secret"}])
def test_audit_logs_reject_bad_paging_and_filters(client_as, params):
    assert client_as("admin").get("/admin/audit-logs", params=params).status_code == 422
