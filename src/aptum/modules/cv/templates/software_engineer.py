from io import BytesIO
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from aptum.modules.cv.document import CVDocument
from aptum.modules.cv.templates.common import p

_INK = "#1F2933"
_ACCENT = "#1F3A5F"
_GRAY = "#52606D"
_RULE = "#B8C2CC"


def _labeled(label: str, value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"<b>{escape(label)}:</b> {escape(value)}", style)


class SoftwareEngineerTemplate:
    """Single column, dark text on white, one navy accent, standard fonts, no images or tables:
    plain text flow for ATS parsers. Skills come before Experience so keywords sit at the top."""

    def render(self, doc: CVDocument) -> bytes:
        body = ParagraphStyle(
            "Body", fontName="Helvetica", fontSize=10, leading=13.5, spaceAfter=2, textColor=HexColor(_INK)
        )
        muted = ParagraphStyle("Muted", parent=body, fontSize=9, leading=12, textColor=HexColor(_GRAY))
        name = ParagraphStyle(
            "Name",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            alignment=TA_CENTER,
            spaceAfter=2,
            textColor=HexColor(_ACCENT),
        )
        headline = ParagraphStyle(
            "Headline",
            parent=body,
            fontName="Helvetica",
            fontSize=11.5,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=4,
            textColor=HexColor(_GRAY),
        )
        contact = ParagraphStyle("Contact", parent=muted, fontSize=9.5, alignment=TA_CENTER, spaceAfter=2)
        links = ParagraphStyle("Links", parent=contact, textColor=HexColor(_ACCENT))
        section = ParagraphStyle(
            "Section",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=10.5,
            spaceBefore=16,
            spaceAfter=1,
            textColor=HexColor(_ACCENT),
        )
        item = ParagraphStyle("Item", parent=body, fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=0)
        bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=0)

        story: list = [p(doc.full_name, name)]
        if doc.headline:
            story.append(p(doc.headline, headline))
        contact_parts = [escape(x) for x in (doc.location, doc.phone, doc.email) if x]
        if contact_parts:
            story.append(Paragraph(" | ".join(contact_parts), contact))
        link_parts = [
            f"<a href={quoteattr(link.url)}>{escape(link.label)}</a>" for link in doc.links
        ]
        if link_parts:
            story.append(Paragraph(" | ".join(link_parts), links))
        story.append(Spacer(1, 0.4 * cm))

        def heading(title: str) -> None:
            story.append(p(title.upper(), section))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor(_RULE), spaceBefore=1, spaceAfter=4))

        if doc.summary or doc.work_authorization_line:
            heading("Summary")
            if doc.work_authorization_line:
                story.append(p(doc.work_authorization_line, muted))
            if doc.summary:
                story.append(p(doc.summary, body))

        if doc.skill_groups:
            heading("Technical Skills")
            for group in doc.skill_groups:
                story.append(_labeled(group.label, ", ".join(group.names), body))

        if doc.experiences:
            heading("Experience")
            for index, exp in enumerate(doc.experiences):
                if index:
                    story.append(Spacer(1, 0.3 * cm))
                story.append(KeepTogether([p(exp.title, item), p(exp.dates, muted)]))
                if exp.description:
                    story.append(p(exp.description, body))
                for text in exp.bullets:
                    story.append(Paragraph(escape(text), bullet, bulletText="•"))
                if exp.skills_line:
                    story.append(_labeled("Technologies", exp.skills_line, muted))

        if doc.projects:
            heading("Projects")
            for project in doc.projects:
                story.append(p(project.name, item))
                if project.description:
                    story.append(p(project.description, body))

        if doc.educations:
            heading("Education")
            for edu in doc.educations:
                story.append(KeepTogether([p(edu.title, item), p(edu.dates, muted)]))
                if edu.description:
                    story.append(p(edu.description, body))

        if doc.certifications:
            heading("Certifications")
            for cert in doc.certifications:
                story.append(KeepTogether([p(cert.title, item), p(cert.dates, muted)]))

        if doc.languages:
            heading("Languages")
            for language in doc.languages:
                story.append(p(language, body))

        buffer = BytesIO()
        SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1 * cm,
            bottomMargin=1 * cm,
            title=f"{doc.full_name} - CV",
            author=doc.full_name,
        ).build(story)
        return buffer.getvalue()
