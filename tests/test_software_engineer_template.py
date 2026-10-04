from conftest import pdf_text
from factories import base_profile

from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate

PORTFOLIO = {"kind": "portfolio", "label": "Portfolio", "url": "https://alex.example.dev", "visible": True}


def _lines(profile) -> list[str]:
    text = pdf_text(SoftwareEngineerTemplate().render(build_cv_data(profile)))
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_header_is_name_tagline_data_then_links_in_saved_order():
    links = [PORTFOLIO, *base_profile().links]
    lines = _lines(base_profile(links=links))
    assert lines[:4] == [
        "Alex Rivera",
        "Senior Software Engineer",
        "Toronto, Canada | +1 555 0100 | alex.rivera@example.com",
        "https://alex.example.dev | https://www.linkedin.com/in/example-alex | https://github.com/example-alex",
    ]


def test_links_line_follows_the_saved_order():
    reordered = list(reversed(base_profile().links))
    assert _lines(base_profile(links=reordered))[3] == (
        "https://github.com/example-alex | https://www.linkedin.com/in/example-alex"
    )
