from conftest import pdf_text
from factories import base_profile

from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate


def _lines(profile) -> list[str]:
    text = pdf_text(SoftwareEngineerTemplate().render(build_cv_data(profile)))
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_header_is_name_tagline_data_then_links():
    lines = _lines(base_profile(portfolio_url="https://alex.example.dev"))
    assert lines[:4] == [
        "Alex Rivera",
        "Senior Software Engineer",
        "Toronto, Canada | +1 555 0100 | alex.rivera@example.com",
        "https://alex.example.dev | https://www.linkedin.com/in/example-alex | https://github.com/example-alex",
    ]


def test_links_line_skips_empty_fields():
    lines = _lines(base_profile())
    assert lines[3] == "https://www.linkedin.com/in/example-alex | https://github.com/example-alex"
