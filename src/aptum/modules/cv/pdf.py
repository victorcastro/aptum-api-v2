from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from aptum.modules.profile.models import Profile


def _month(value: date | None) -> str:
    return value.strftime("%b %Y") if value else ""


def _range(start: date | None, end: date | None, current: bool = False) -> str:
    if start is None and end is None:
        return ""
    return f"{_month(start)} - {'Present' if current else _month(end)}".strip(" -")


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def render_cv_pdf(profile: Profile) -> bytes:
    base = getSampleStyleSheet()
    name_style = ParagraphStyle("Name", parent=base["Title"], alignment=0, spaceAfter=2)
    section = ParagraphStyle("Section", parent=base["Heading2"], spaceBefore=12, spaceAfter=4)
    item = ParagraphStyle("Item", parent=base["Heading4"], spaceBefore=6, spaceAfter=0)
    body = base["BodyText"]
    muted = ParagraphStyle("Muted", parent=body, textColor="#555555")
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=0)

    story: list = []
    full_name = " ".join(part for part in (profile.first_name, profile.last_name) if part)
    story.append(_p(full_name or "Curriculum Vitae", name_style))
    if profile.headline:
        story.append(_p(profile.headline, body))
    location = ", ".join(x for x in (profile.city, profile.region, profile.country_code) if x)
    contact = " | ".join(x for x in (profile.contact_email, profile.phone, location) if x)
    if contact:
        story.append(_p(contact, muted))
    if profile.links:
        story.append(_p(" | ".join(link.label or link.url for link in profile.links), muted))

    if profile.summary:
        story.append(_p("Summary", section))
        story.append(_p(profile.summary, body))

    if profile.experiences:
        story.append(_p("Experience", section))
        for exp in profile.experiences:
            where = exp.employer.name + (f" (client: {exp.client.name})" if exp.client else "")
            story.append(_p(f"{exp.position} - {where}", item))
            story.append(_p(_range(exp.start_date, exp.end_date, exp.is_current), muted))
            if exp.description:
                story.append(_p(exp.description, body))
            for function in exp.functions:
                story.append(Paragraph(escape(function.description), bullet, bulletText="•"))
            if exp.skills:
                story.append(_p("Skills: " + ", ".join(s.name for s in exp.skills), muted))

    if profile.educations:
        story.append(_p("Education", section))
        for edu in profile.educations:
            degree = edu.degree + (f", {edu.field_of_study}" if edu.field_of_study else "")
            story.append(_p(f"{degree} - {edu.institution}", item))
            story.append(_p(_range(edu.start_date, edu.end_date), muted))
            if edu.description:
                story.append(_p(edu.description, body))

    if profile.skills:
        story.append(_p("Skills", section))
        story.append(_p(", ".join(ps.skill.name for ps in profile.skills), body))

    if profile.languages:
        story.append(_p("Languages", section))
        story.append(
            _p(
                ", ".join(
                    f"{lang.language_code.upper()} ({lang.proficiency.value.replace('_', ' ')})"
                    for lang in profile.languages
                ),
                body,
            )
        )

    if profile.certifications:
        story.append(_p("Certifications", section))
        for cert in profile.certifications:
            story.append(_p(f"{cert.name} - {cert.issuing_organization}", item))
            story.append(_p(_range(cert.issue_date, cert.expiration_date), muted))

    if profile.projects:
        story.append(_p("Projects", section))
        for project in profile.projects:
            story.append(_p(project.name, item))
            if project.description:
                story.append(_p(project.description, body))

    story.append(Spacer(1, 0.2 * cm))
    buffer = BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm
    ).build(story)
    return buffer.getvalue()
