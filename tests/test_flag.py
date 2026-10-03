"""ATS_CV_ENABLED off must behave exactly like 1.0.0; on, the new endpoints work.

The golden files were produced by the 1.0.0 code (before any 1.1.0 change) from the same
synthetic profile, so they pin the legacy PDF output."""

from pathlib import Path

import pytest
from conftest import pdf_text
from factories import base_profile
from fastapi.testclient import TestClient

from aptum.core.dependencies import get_current_user, get_db
from aptum.main import app
from aptum.modules.matching.service import MatchingService
from aptum.modules.profile.service import ProfileService

GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def profile(monkeypatch):
    profile = base_profile()
    monkeypatch.setattr(ProfileService, "get_or_create", lambda self, user_id: profile)
    return profile


@pytest.fixture
def client(profile):
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"id": profile.user_id})()
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.parametrize("template", ["classic", "software-engineer"])
def test_flag_off_export_is_identical_to_1_0_0(client, profile, template):
    profile.preferred_template = template
    response = client.get("/cv/export")
    assert response.status_code == 200
    assert pdf_text(response.content) == (GOLDEN / f"legacy_{template}.txt").read_text()


def test_flag_off_new_fields_set_still_legacy_output(client, profile):
    profile.preferred_template = "classic"
    profile.english_level, profile.work_authorization, profile.github_url = "C1", "authorized", "https://github.com/x"
    profile.experiences[0].area = "ai"
    assert pdf_text(client.get("/cv/export").content) == (GOLDEN / "legacy_classic.txt").read_text()


def test_flag_off_ats_endpoints_are_404(client):
    assert client.post("/cv/ats/export", json={}).status_code == 404
    assert client.post("/cv/ats/report", json={"job_description": "Python"}).status_code == 404


def test_flag_off_matching_prompt_unchanged(monkeypatch):
    prompts = []

    class LLM:
        def generate(self, prompt):
            prompts.append(prompt)
            return ""

    service = MatchingService.__new__(MatchingService)
    service.repository = type("R", (), {"get_profile_embedding": lambda s, u: None, "get_profile": lambda s, u: base_profile()})()
    service.embedding_client = type("E", (), {"embed": lambda s, t: []})()
    service.llm_client = LLM()
    service.match(1, "Job")
    assert prompts == ["Tailor this candidate's CV for the following job:\nJob"]


def test_flag_on_export_uses_ats_and_explicit_template_keeps_legacy(client, profile, set_flag):
    set_flag(True)
    text = pdf_text(client.get("/cv/export").content)
    assert "LLMs & AI: OpenAI API, RAG" in text and "TECHNICAL SKILLS" not in text
    legacy = pdf_text(client.get("/cv/export", params={"template": "classic"}).content)
    assert legacy == (GOLDEN / "legacy_classic.txt").read_text()


def test_flag_on_report_and_export(client, set_flag):
    set_flag(True)
    body = {"job_description": "AI Engineer with Python, RAG and Kubernetes"}
    report = client.post("/cv/ats/report", json=body)
    assert report.status_code == 200
    data = report.json()
    assert data["page_count"] <= 2
    assert data["years_of_experience"]["total"] >= 1
    assert data["skills"][0] == {"category": "LLMs & AI", "names": ["RAG", "OpenAI API"]}
    assert data["fidelity_issues"] == []
    assert data["keyword_coverage"]["missing"] == ["Kubernetes"]
    assert any(w["code"] == "missing_metric" for w in data["warnings"])

    pdf = client.post("/cv/ats/export", json=body)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert "SKILLS" in pdf_text(pdf.content)


def test_flag_on_matching_prompt_has_locked_years(set_flag):
    set_flag(True)
    prompts = []
    service = MatchingService.__new__(MatchingService)
    service.repository = type("R", (), {"get_profile_embedding": lambda s, u: None, "get_profile": lambda s, u: base_profile()})()
    service.embedding_client = type("E", (), {"embed": lambda s, t: []})()
    service.llm_client = type("L", (), {"generate": lambda s, p: prompts.append(p) or ""})()
    service.match(1, "Job")
    assert "LOCKED FACTS" in prompts[0] and "Total professional experience:" in prompts[0]
