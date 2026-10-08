from io import BytesIO

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
        "Toronto, Ontario, Canada | +1 555 0100 | alex.rivera@example.com",
        "https://alex.example.dev | https://www.linkedin.com/in/example-alex | https://github.com/example-alex",
    ]


def test_links_line_follows_the_saved_order():
    reordered = list(reversed(base_profile().links))
    assert _lines(base_profile(links=reordered))[3] == (
        "https://github.com/example-alex | https://www.linkedin.com/in/example-alex"
    )


def test_dated_line_draws_for_plain_wrapped_and_escaped_titles():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfgen.canvas import Canvas

    from aptum.modules.cv.templates.software_engineer import _DatedLine

    style = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=10, leading=13)
    for title in ("Engineer", "R&D Engineer", "Senior Engineer & Lead at a very long company name " * 6):
        line = _DatedLine(title, "2020-01 - 2022-03", style, style)
        line.wrap(400, 800)
        line.canv = Canvas(BytesIO())
        line.draw()


def test_institution_and_issuer_sit_below_their_title():
    lines = _lines(base_profile())
    degree = next(i for i, line in enumerate(lines) if line.startswith("BSc, Computer Science"))
    assert "Lakeside University" not in lines[degree]
    assert "Lakeside University" in lines[degree + 1 : degree + 3]
    cert = next(i for i, line in enumerate(lines) if line.startswith("Cloud Practitioner"))
    assert "Example Cloud Institute" not in lines[cert]
    assert "Example Cloud Institute" in lines[cert + 1 : cert + 3]


def test_certification_link_is_printed_after_the_issuer():
    profile = base_profile()
    profile.certifications[0].credential_url = "https://verify.example.dev/abc123"
    lines = _lines(profile)
    cert = next(i for i, line in enumerate(lines) if line.startswith("Cloud Practitioner"))
    assert any(
        line == "Example Cloud Institute | https://verify.example.dev/abc123" for line in lines[cert + 1 : cert + 3]
    )


def test_certification_link_is_hidden_when_the_user_turns_it_off():
    profile = base_profile()
    profile.certifications[0].credential_url = "https://verify.example.dev/abc123"
    profile.certifications[0].show_credential_url = False
    assert not any("verify.example.dev" in line for line in _lines(profile))


def test_project_link_is_printed_and_can_be_hidden():
    profile = base_profile()
    profile.projects[0].url = "https://github.com/example-alex/cli"
    assert any("github.com/example-alex/cli" in line for line in _lines(profile))
    profile.projects[0].show_url = False
    assert not any("github.com/example-alex/cli" in line for line in _lines(profile))


def test_inactive_language_is_not_printed():
    profile = base_profile()
    profile.languages[0].is_active = False
    name = profile.languages[0].language.name
    assert not any(name in line for line in _lines(profile))
