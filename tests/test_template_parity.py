from io import BytesIO

import pytest
from conftest import pdf_text
from docx import Document
from factories import base_profile

from aptum.modules.cv.ats.pipeline import generate_ats_cv
from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.docx_render import render_cv_docx
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate

PROJECT_URL = "https://github.com/example-alex/cli"
CERT_URL = "https://verify.example.dev/abc123"
CERT_LINK_TEXT = "Verifycredential"  # the credential link text, squashed like the rendered text


def _squash(text: str) -> str:
    return "".join(text.split())


def _basic(profile) -> str:
    return _squash(pdf_text(generate_ats_cv(profile).pdf))


def _software_engineer(profile) -> str:
    return _squash(pdf_text(SoftwareEngineerTemplate().render(build_cv_data(profile))))


def _docx(profile) -> str:
    document = Document(BytesIO(render_cv_docx(build_cv_data(profile))))
    return _squash("".join(p.text for p in document.paragraphs))


RENDERERS = {"basic": _basic, "software-engineer": _software_engineer, "docx": _docx}


def _with_urls(profile):
    profile.projects[0].url = PROJECT_URL
    profile.certifications[0].credential_url = CERT_URL


def _hide_project_url(profile):
    _with_urls(profile)
    profile.projects[0].show_url = False


def _hide_cert_url(profile):
    _with_urls(profile)
    profile.certifications[0].show_credential_url = False


def _inactive(collection: str):
    def mutate(profile):
        getattr(profile, collection)[0].is_active = False

    return mutate


def _years_only_education(profile):
    edu = profile.educations[0]
    edu.start_date = edu.end_date = None
    edu.start_year, edu.end_year = 2008, 2012


CASES = [
    pytest.param(_with_urls, PROJECT_URL, True, id="project-url-shown"),
    pytest.param(_hide_project_url, PROJECT_URL, False, id="project-url-hidden"),
    pytest.param(_with_urls, CERT_LINK_TEXT, True, id="credential-url-shown"),
    pytest.param(_hide_cert_url, CERT_LINK_TEXT, False, id="credential-url-hidden"),
    pytest.param(lambda profile: None, "ExampleCloudInstitute", True, id="certification-issuer"),
    pytest.param(lambda profile: None, "FastAPI,Docker,AWS", True, id="experience-technologies"),
    pytest.param(_years_only_education, "2008-2012", True, id="education-years-only"),
    pytest.param(_inactive("projects"), "Open-sourceCLI", False, id="inactive-project"),
    pytest.param(_inactive("certifications"), "CloudPractitioner", False, id="inactive-certification"),
    pytest.param(_inactive("educations"), "LakesideUniversity", False, id="inactive-education"),
    pytest.param(_inactive("experiences"), "NorthwindLabs", False, id="inactive-experience"),
    pytest.param(_inactive("languages"), "Spanish", False, id="inactive-language"),
]


@pytest.mark.parametrize("renderer", RENDERERS.values(), ids=RENDERERS.keys())
@pytest.mark.parametrize(("mutate", "needle", "present"), CASES)
def test_every_template_shows_and_hides_the_same_data(renderer, mutate, needle, present):
    profile = base_profile()
    mutate(profile)
    assert (needle in renderer(profile)) is present
