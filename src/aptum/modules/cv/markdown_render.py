import re

from aptum.modules.cv.document import CVDocument
from aptum.modules.cv.links import (
    CREDENTIAL_LINK_TEXT,
    format_link_display,
    normalize_link_href,
)

_SPECIAL = re.compile(r"([\\*_\[\]`])")


def _esc(text: str) -> str:
    """Escape Markdown syntax in plain fields (names, titles, issuers). Free text written by the
    user (summary, descriptions, bullets) is already Markdown (`common/richtext.py`) and is not escaped."""
    return _SPECIAL.sub(r"\\\1", text)


def _link(label: str, href: str) -> str:
    return f"[{_esc(label)}]({href})"


def _bullet(text: str) -> str:
    return "- " + text.strip().replace("\n", "\n  ")


def render_cv_markdown(doc: CVDocument) -> str:
    """The CV as Markdown for pasting into another AI agent. Same data and section order as the modern
    template, with no page limit. Empty sections are left out."""
    blocks: list[str] = [f"# {_esc(doc.full_name)}"]
    if doc.headline:
        blocks.append(f"**{_esc(doc.headline)}**")
    if doc.availability_line:
        blocks.append(_esc(doc.availability_line))
    contact = [_esc(doc.phone)] if doc.phone else []
    if doc.email:
        contact.append(_link(doc.email, f"mailto:{doc.email}"))
    if contact:
        blocks.append(" | ".join(contact))
    if doc.links:
        blocks.append(" | ".join(_link(link.label, link.url) for link in doc.links))

    if doc.summary:
        blocks += ["## Summary", doc.summary.strip()]

    if doc.skill_groups:
        blocks.append("## Technical Skills")
        blocks.append(
            "\n".join(f"- **{_esc(group.label)}:** {_esc(', '.join(group.names))}" for group in doc.skill_groups)
        )

    if doc.experiences:
        blocks.append("## Experience")
        for exp in doc.experiences:
            blocks.append(f"### {_esc(exp.title)}" + (f"\n*{exp.dates}*" if exp.dates else ""))
            if exp.description:
                blocks.append(exp.description.strip())
            if exp.bullets:
                blocks.append("\n".join(_bullet(text) for text in exp.bullets))
            if exp.skills_line:
                blocks.append(f"**Technologies:** {_esc(exp.skills_line)}")

    if doc.projects:
        blocks.append("## Projects")
        for project in doc.projects:
            blocks.append(f"### {_esc(project.name)}")
            if project.description:
                blocks.append(project.description.strip())
            if project.url:
                blocks.append(_link(format_link_display(project.url), normalize_link_href(project.url)))

    if doc.educations:
        blocks.append("## Education")
        for edu in doc.educations:
            blocks.append(f"### {_esc(edu.title)}")
            blocks.append(" | ".join(part for part in (_esc(edu.place), f"*{edu.dates}*" if edu.dates else "") if part))

    if doc.certifications:
        blocks.append("## Certifications")
        for cert in doc.certifications:
            parts = [_esc(cert.issuer)]
            if cert.dates:
                parts.append(f"*{cert.dates}*")
            if cert.url:
                parts.append(_link(CREDENTIAL_LINK_TEXT, normalize_link_href(cert.url)))
            blocks.append(f"### {_esc(cert.title)}\n" + " | ".join(parts))

    if doc.languages:
        blocks.append("## Languages")
        blocks.append("\n".join(f"- {_esc(language)}" for language in doc.languages))

    return "\n\n".join(blocks) + "\n"
