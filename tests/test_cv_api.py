"""CV endpoints: the ATS pipeline is the default; legacy templates only on explicit request.

The golden files were produced by the 1.0.0 code from the same synthetic profile, so they pin
the legacy templates' output for `?template=`."""

from io import BytesIO
from pathlib import Path

import pytest
from conftest import pdf_text
from factories import base_profile
from fastapi.testclient import TestClient
from pypdf import PdfReader

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


def test_default_export_is_ats_even_with_a_saved_template(client, profile):
    profile.preferred_template = "software-engineer"
    response = client.get("/cv/export")
    assert response.status_code == 200
    text = pdf_text(response.content)
    assert "LLMs & AI: OpenAI API, RAG" in text and "TECHNICAL SKILLS" not in text


def test_explicit_template_renders_the_legacy_layout_unchanged(client):
    response = client.get("/cv/export", params={"template": "software-engineer"})
    assert pdf_text(response.content) == (GOLDEN / "legacy_software-engineer.txt").read_text()


def test_languages_section_matches_between_templates(client):
    default = pdf_text(client.get("/cv/export").content)
    explicit = pdf_text(client.get("/cv/export", params={"template": "software-engineer"}).content)
    for text in (default, explicit):
        assert "Spanish - Native" in text
        assert "English - C1" in text


@pytest.mark.parametrize("params", [{}, {"template": "software-engineer"}])
def test_every_template_is_a4(client, params):
    page = PdfReader(BytesIO(client.get("/cv/export", params=params).content)).pages[0]
    assert (round(float(page.mediabox.width)), round(float(page.mediabox.height))) == (595, 842)


def test_classic_template_is_gone(client):
    assert client.get("/cv/export", params={"template": "classic"}).status_code == 404


def test_unknown_template_is_404(client):
    assert client.get("/cv/export", params={"template": "nope"}).status_code == 404


def test_report_and_export(client):
    body = {"job_description": "AI Engineer with Python, RAG and Kubernetes"}
    report = client.post("/cv/ats/report", json=body)
    assert report.status_code == 200
    data = report.json()
    assert data["page_count"] <= 2
    assert data["years_of_experience"]["total"] >= 1
    assert data["skills"][0] == {"category": "LLMs & AI", "names": ["RAG", "OpenAI API"]}  # offer-relevant first
    assert data["fidelity_issues"] == []
    assert data["keyword_coverage"]["missing"] == ["Kubernetes"]
    assert any(w["code"] == "missing_metric" for w in data["warnings"])

    pdf = client.post("/cv/ats/export", json=body)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert "SKILLS" in pdf_text(pdf.content)


def test_report_without_offer_has_no_keyword_coverage(client):
    data = client.post("/cv/ats/report", json={}).json()
    assert data["keyword_coverage"] is None


def test_matching_prompt_has_locked_years():
    prompts = []
    service = MatchingService.__new__(MatchingService)
    service.repository = type(
        "R", (), {"get_profile_embedding": lambda s, u: None, "get_profile": lambda s, u: base_profile()}
    )()
    service.embedding_client = type("E", (), {"embed": lambda s, t: []})()
    service.llm_client = type("L", (), {"generate": lambda s, p: prompts.append(p) or ""})()
    service.match(1, "Job")
    assert prompts[0].startswith("Tailor this candidate's CV for the following job:\nJob")
    assert "LOCKED FACTS" in prompts[0] and "Total professional experience:" in prompts[0]
