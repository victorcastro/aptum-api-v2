"""CV endpoints: basic (the ATS pipeline) is the default; the saved preference or `?template=` picks another.

The golden files were produced by the 1.0.0 code from the same synthetic profile, so they pin
the legacy templates' output for `?template=`. Since 1.1.0 the skills are grouped by
`profile_skills.category_id` (the catalog `skills.category` is gone)."""

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


def test_default_export_is_basic_without_a_saved_template(client):
    response = client.get("/cv/export")
    assert response.status_code == 200
    text = pdf_text(response.content)
    assert "LLMs & AI: OpenAI API, RAG" in text and "TECHNICAL SKILLS" not in text


def test_default_export_uses_the_saved_template(client, profile):
    profile.preferred_template = "software-engineer"
    text = pdf_text(client.get("/cv/export").content)
    assert text == (GOLDEN / "legacy_software-engineer.txt").read_text()


def test_explicit_template_overrides_the_saved_one(client, profile):
    profile.preferred_template = "software-engineer"
    text = pdf_text(client.get("/cv/export", params={"template": "basic"}).content)
    assert "LLMs & AI: OpenAI API, RAG" in text and "TECHNICAL SKILLS" not in text


def test_docx_export_returns_an_editable_word_file(client, profile):
    profile.preferred_template = "basic"
    response = client.get("/cv/export", params={"format": "docx"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.headers["content-disposition"].endswith('.docx"')
    assert response.content.startswith(b"PK")


def test_unknown_export_format_is_rejected(client):
    assert client.get("/cv/export", params={"format": "xml"}).status_code == 422


def test_templates_list_basic_first_and_selected_by_default(client):
    templates = client.get("/cv/templates").json()
    assert [t["id"] for t in templates] == ["basic", "software-engineer"]
    assert [t["selected"] for t in templates] == [True, False]


def test_saved_template_is_the_selected_one(client, profile):
    profile.preferred_template = "software-engineer"
    templates = client.get("/cv/templates").json()
    assert [(t["id"], t["selected"]) for t in templates] == [("basic", False), ("software-engineer", True)]
    assert client.get("/cv/settings").json() == {"template_id": "software-engineer"}


def test_basic_can_be_saved_as_the_default(client, profile, monkeypatch):
    profile.preferred_template = "software-engineer"

    def save(self, saved_profile, template_id):
        saved_profile.preferred_template = template_id
        return saved_profile

    monkeypatch.setattr(ProfileService, "set_preferred_template", save)
    response = client.patch("/cv/settings", json={"template_id": "basic"})
    assert response.status_code == 200
    assert response.json() == {"template_id": "basic"}
    assert profile.preferred_template == "basic"


def test_saving_an_unknown_template_is_404(client):
    assert client.patch("/cv/settings", json={"template_id": "nope"}).status_code == 404


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
        "R", (), {"get_profile": lambda s, u: base_profile()}
    )()
    service.embedding_client = type("E", (), {"embed": lambda s, t: []})()
    service.llm_client = type("L", (), {"generate": lambda s, p: prompts.append(p) or ""})()
    service.match(1, "Job")
    assert prompts[0].startswith("Tailor this candidate's CV for the following job:\nJob")
    assert "LOCKED FACTS" in prompts[0] and "Total professional experience:" in prompts[0]


@pytest.mark.parametrize("params", [{}, {"template": "software-engineer"}])
def test_availability_line_sits_in_the_header_and_never_mentions_sponsorship(client, profile, params):
    profile.work_authorization = "requires_sponsorship"
    profile.work_authorization_country = "PE"
    profile.open_to_relocation = True
    lines = [line.strip() for line in pdf_text(client.get("/cv/export", params=params).content).splitlines()]
    assert lines[2] == "Toronto, Canada | Open to relocation"
    assert not any("sponsorship" in line.lower() for line in lines)
