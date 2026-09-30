from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate

from aptum.modules.cv.document import CVDocument
from aptum.modules.cv.templates.common import NumberedCanvas, p

_GRAY = "#444444"


def _labeled(label: str, value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"<b>{escape(label)}:</b> {escape(value)}", style)


class SoftwareEngineerTemplate:
    """Single column, black text on white, no images or tables: plain text flow for ATS parsers.
    Skills come before Experience so keywords sit at the top."""

    def render(self, doc: CVDocument) -> bytes:
        body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=13, spaceAfter=2)
        muted = ParagraphStyle("Muted", parent=body, fontSize=9, textColor=_GRAY)
        name = ParagraphStyle("Name", parent=body, fontName="Helvetica-Bold", fontSize=18, leading=22)
        headline = ParagraphStyle("Headline", parent=body, fontSize=11, leading=14)
        section = ParagraphStyle(
            "Section", parent=body, fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=10, spaceAfter=1
        )
        item = ParagraphStyle("Item", parent=body, fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=0)
        bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=0)

        story: list = [p(doc.full_name, name)]
        if doc.headline:
            story.append(p(doc.headline, headline))
        if doc.contact_line:
            story.append(p(doc.contact_line, muted))
        if doc.links_line:
            story.append(p(doc.links_line, muted))

        def heading(title: str) -> None:
            story.append(p(title.upper(), section))
            story.append(HRFlowable(width="100%", thickness=0.5, color=black, spaceBefore=1, spaceAfter=4))

        if doc.summary:
            heading("Summary")
            story.append(p(doc.summary, body))

        if doc.skill_groups:
            heading("Technical Skills")
            for group in doc.skill_groups:
                story.append(_labeled(group.label, ", ".join(group.names), body))

        if doc.experiences:
            heading("Experience")
            for exp in doc.experiences:
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

        if doc.languages_line:
            heading("Languages")
            story.append(p(doc.languages_line, body))

        buffer = BytesIO()
        SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.8 * cm,
            bottomMargin=2 * cm,
            title=f"{doc.full_name} - CV",
            author=doc.full_name,
        ).build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()
