from factories import base_profile

from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.markdown_render import render_cv_markdown


def _md(profile=None) -> str:
    return render_cv_markdown(build_cv_data(profile or base_profile()))


def _headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("## ")]


def test_header_has_name_headline_contact_and_links():
    lines = _md().splitlines()
    assert lines[0] == "# Alex Rivera"
    assert "**Senior Software Engineer**" in lines
    assert "[alex.rivera@example.com](mailto:alex.rivera@example.com)" in _md()
    assert "[linkedin.com/in/example-alex](https://www.linkedin.com/in/example-alex)" in _md()


def test_sections_follow_the_modern_order():
    profile = base_profile()
    profile.projects[0].url = "https://github.com/example-alex/cli"
    assert _headings(_md(profile)) == [
        "## Summary",
        "## Technical Skills",
        "## Experience",
        "## Projects",
        "## Education",
        "## Certifications",
        "## Languages",
    ]


def test_experience_has_title_dates_bullets_and_technologies():
    text = _md()
    assert "### AI Engineer - Northwind Labs\n*Jan 2023 - Present*" in text
    assert "- Built a RAG assistant" in text
    assert "**Technologies:** Python, OpenAI API, RAG" in text


def test_skills_are_one_bold_line_per_category():
    assert "- **LLMs & AI:** OpenAI API, RAG" in _md()


def test_project_and_credential_links_are_markdown_links():
    profile = base_profile()
    profile.projects[0].url = "https://github.com/example-alex/cli"
    profile.certifications[0].credential_url = "https://verify.example.dev/abc123"
    text = _md(profile)
    assert "[github.com/example-alex/cli](https://github.com/example-alex/cli)" in text
    assert "[Verify credential](https://verify.example.dev/abc123)" in text


def test_hidden_urls_and_inactive_items_are_left_out():
    profile = base_profile()
    profile.projects[0].url = "https://github.com/example-alex/cli"
    profile.projects[0].show_url = False
    profile.experiences[0].is_active = False
    text = _md(profile)
    assert "github.com/example-alex/cli" not in text
    assert "Northwind Labs" not in text


def test_empty_sections_are_omitted():
    profile = base_profile()
    for collection in (profile.projects, profile.certifications, profile.languages):
        for item in collection:
            item.is_active = False
    headings = _headings(_md(profile))
    assert "## Projects" not in headings and "## Certifications" not in headings and "## Languages" not in headings


def test_rich_text_is_kept_and_plain_fields_are_escaped():
    profile = base_profile(summary="Builds **fast** APIs.")
    profile.experiences[0].position = "Lead [Platform] *Team*"
    text = _md(profile)
    assert "Builds **fast** APIs." in text
    assert r"### Lead \[Platform\] \*Team\* - Northwind Labs" in text
