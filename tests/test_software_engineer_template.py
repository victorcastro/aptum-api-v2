from io import BytesIO

from conftest import pdf_text
from factories import base_profile

from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate

PORTFOLIO = {"kind": "portfolio", "label": "Portfolio", "url": "https://alex.example.dev", "visible": True}


def _lines(profile) -> list[str]:
    text = pdf_text(SoftwareEngineerTemplate().render(build_cv_data(profile)))
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_header_is_name_title_availability_contact_then_links_by_kind():
    links = [PORTFOLIO, *reversed(base_profile().links)]
    profile = base_profile(
        links=links, work_authorization="authorized", work_authorization_country="CA", work_preferences=["hybrid"]
    )
    assert _lines(profile)[:5] == [
        "Alex Rivera",
        "Senior Software Engineer",
        "Toronto, Canada | Open to hybrid | Authorized to work in Canada",
        "+1 555 0100 | alex.rivera@example.com",
        "linkedin.com/in/example-alex | github.com/example-alex | alex.example.dev",
    ]


def test_header_links_are_clickable_with_full_urls():
    from pypdf import PdfReader

    page = PdfReader(BytesIO(SoftwareEngineerTemplate().render(build_cv_data(base_profile())))).pages[0]
    targets = [str(annot.get_object()["/A"]["/URI"]) for annot in page["/Annots"]]
    assert targets[:3] == [
        "mailto:alex.rivera@example.com",
        "https://www.linkedin.com/in/example-alex",
        "https://github.com/example-alex",
    ]


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
        line == "Example Cloud Institute | Verify credential" for line in lines[cert + 1 : cert + 3]
    )


def test_project_link_keeps_the_full_url():
    profile = base_profile()
    profile.projects[0].url = "https://github.com/example-alex/cli"
    assert "https://github.com/example-alex/cli" in _lines(profile)


def test_certification_link_is_hidden_when_the_user_turns_it_off():
    profile = base_profile()
    profile.certifications[0].credential_url = "https://verify.example.dev/abc123"
    profile.certifications[0].show_credential_url = False
    assert not any("verify.example.dev" in line or "Verify credential" in line for line in _lines(profile))


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
