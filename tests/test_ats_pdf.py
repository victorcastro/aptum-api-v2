import re
from datetime import date
from io import BytesIO

from conftest import pdf_text
from factories import base_profile
from pypdf import PdfReader

from aptum.modules.cv.ats.pipeline import generate_ats_cv

TODAY = date(2026, 10, 1)


def _profile(**fields):
    defaults = {
        "work_authorization": "authorized",
        "work_authorization_country": "CA",
        "links": [
            {"kind": "portfolio", "label": "Portfolio", "url": "https://alex.example.dev", "visible": True},
            {"kind": "linkedin", "label": "LinkedIn", "url": "https://www.linkedin.com/in/example-alex", "visible": True},
            {"kind": "github", "label": "GitHub", "url": "https://github.com/example-alex", "visible": True},
        ],
    }
    return base_profile(**{**defaults, **fields})


def _lines(pdf: bytes) -> list[str]:
    return [line.strip() for line in pdf_text(pdf).splitlines() if line.strip()]


def test_text_is_selectable_and_headings_are_standard_and_ordered():
    result = generate_ats_cv(_profile(), today=TODAY)
    lines = _lines(result.pdf)
    headings = [line for line in lines if line.isupper() and line.isalpha()]
    assert headings == ["SUMMARY", "EXPERIENCE", "SKILLS", "EDUCATION", "CERTIFICATIONS", "PROJECTS", "LANGUAGES"]
    assert lines[0] == "Alex Rivera"


def _link_targets(page) -> list[str]:
    annots = [annot.get_object() for annot in page.get("/Annots") or []]
    assert all(annot["/Subtype"] == "/Link" for annot in annots)
    return [str(annot["/A"]["/URI"]) for annot in annots]


def test_nothing_is_an_image_or_table_and_only_header_links_are_annotations():
    reader = PdfReader(BytesIO(generate_ats_cv(_profile(), today=TODAY).pdf))
    assert _link_targets(reader.pages[0]) == [
        "mailto:alex.rivera@example.com",
        "https://www.linkedin.com/in/example-alex",
        "https://github.com/example-alex",
        "https://alex.example.dev",
    ]
    for page in reader.pages:
        assert list(page.images) == []
        resources = page.get("/Resources") or {}
        assert "/XObject" not in resources  # no images or form boxes
        fonts = {str(font.get_object()["/BaseFont"]) for font in resources["/Font"].values()}
        assert fonts <= {"/Helvetica", "/Helvetica-Bold"}


def test_header_is_name_title_availability_contact_then_links():
    profile = _profile(open_to_relocation=True, timezone_label="EST", work_preferences=["remote"])
    lines = _lines(generate_ats_cv(profile, today=TODAY).pdf)
    assert lines[: lines.index("SUMMARY")] == [
        "Alex Rivera",
        "Senior Software Engineer",
        "Toronto, Canada (EST) | Open to remote | Authorized to work in Canada | Open to relocation",
        "+1 555 0100 | alex.rivera@example.com",
        "linkedin.com/in/example-alex | github.com/example-alex | alex.example.dev",
    ]


def test_sponsorship_need_is_never_printed():
    text = pdf_text(generate_ats_cv(_profile(work_authorization="requires_sponsorship"), today=TODAY).pdf)
    assert "Authorized" not in text and "sponsorship" not in text.lower() and "visa" not in text.lower()
    assert "Toronto, Canada\n" in text


def test_work_authorization_line_absent_when_not_set():
    text = pdf_text(generate_ats_cv(base_profile(), today=TODAY).pdf)
    assert "Authorized" not in text and "sponsorship" not in text and "relocation" not in text


def test_dates_are_consistent_mon_yyyy():
    lines = _lines(generate_ats_cv(_profile(), today=TODAY).pdf)
    date_lines = [line for line in lines if re.search(r"\b(19|20)\d{2}\b", line) and " - " in line and len(line) < 25]
    assert date_lines, "expected date lines"
    pattern = re.compile(r"^[A-Z][a-z]{2} \d{4} - ([A-Z][a-z]{2} \d{4}|Present)$")
    assert all(pattern.match(line) for line in date_lines), date_lines
    assert "Jan 2023 - Present" in lines


def test_languages_print_name_and_level_code():
    lines = _lines(generate_ats_cv(_profile(), today=TODAY).pdf)
    assert "Spanish - Native" in lines and "English - C1" in lines


def test_education_year_fallback():
    profile = _profile()
    edu = profile.educations[0]
    edu.start_date = edu.end_date = None
    edu.start_year, edu.end_year = 2008, 2012
    assert "2008 - 2012" in _lines(generate_ats_cv(profile, today=TODAY).pdf)


def test_skills_section_one_line_per_category():
    lines = _lines(generate_ats_cv(_profile(), today=TODAY).pdf)
    start = lines.index("SKILLS")
    assert lines[start + 1 : start + 3] == ["LLMs & AI: OpenAI API, RAG", "Backend: Python, FastAPI"]  # by evidence


def test_warnings_never_end_up_in_the_pdf():
    result = generate_ats_cv(_profile(), today=TODAY)
    assert result.warnings
    text = pdf_text(result.pdf)
    assert "metric" not in text.lower() and "warning" not in text.lower()
