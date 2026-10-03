from dataclasses import dataclass
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.colors import black
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from aptum.modules.cv.ats.document import ATSDocument
from aptum.modules.cv.templates.common import p

# Standard headings, in the order ATS parsers expect them.
SECTION_HEADINGS = ("Summary", "Experience", "Skills", "Education", "Certifications", "Projects", "Languages")


@dataclass(frozen=True)
class RenderedPDF:
    content: bytes
    pages: int


class ATSTemplate:
    """ATS-safe layout: one column of plain text in a standard font (Helvetica), black on white.
    No tables, images, icons, charts, drawn lines, text boxes or photo; links are printed as
    visible URLs. US Letter, the common size for US/Canada (also prints fine on A4)."""

    def render(self, doc: ATSDocument) -> RenderedPDF:
        body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=12.5, spaceAfter=1, textColor=black)
        header = ParagraphStyle("Header", parent=body, fontSize=9.5, leading=12)
        name = ParagraphStyle("Name", parent=body, fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=2)
        headline = ParagraphStyle("Headline", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=14)
        section = ParagraphStyle(
            "Section", parent=body, fontName="Helvetica-Bold", fontSize=11.5, leading=14, spaceBefore=18, spaceAfter=4
        )
        item = ParagraphStyle("Item", parent=body, fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=0)
        bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=2)

        story: list = [p(doc.full_name, name)]
        if doc.headline:
            story.append(p(doc.headline, headline))
        for line in (doc.contact_line, " | ".join(doc.links), doc.work_authorization_line):
            if line:
                story.append(p(line, header))

        def heading(title: str) -> None:
            story.append(p(title.upper(), section))

        if doc.summary:
            heading("Summary")
            story.append(p(doc.summary, body))

        if doc.experiences:
            heading("Experience")
            for exp in doc.experiences:
                story.append(KeepTogether([p(exp.title, item), p(exp.dates, body)]))
                if exp.description:
                    story.append(p(exp.description, body))
                for text in exp.bullets:
                    story.append(Paragraph(escape(text), bullet, bulletText="•"))

        if doc.skill_lines:
            heading("Skills")
            for line in doc.skill_lines:
                story.append(
                    Paragraph(f"<b>{escape(line.category.value)}:</b> {escape(', '.join(line.names))}", body)
                )

        if doc.educations:
            heading("Education")
            for edu in doc.educations:
                story.append(KeepTogether([p(edu.title, item), *([p(edu.dates, body)] if edu.dates else [])]))
                if edu.description:
                    story.append(p(edu.description, body))

        if doc.certifications:
            heading("Certifications")
            for cert in doc.certifications:
                story.append(p(f"{cert.title}{f' ({cert.dates})' if cert.dates else ''}", body))

        if doc.projects:
            heading("Projects")
            for project in doc.projects:
                text = f"<b>{escape(project.name)}</b>"
                if project.description:
                    text += f": {escape(project.description)}"
                story.append(Paragraph(text, body))

        if doc.languages:
            heading("Languages")
            for language in doc.languages:
                story.append(p(language, body))

        story.append(Spacer(1, 0.1 * cm))
        buffer = BytesIO()
        pdf = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            leftMargin=1.8 * cm,
            rightMargin=1.8 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            title=f"{doc.full_name} - CV",
            author=doc.full_name,
        )
        pdf.build(story)
        return RenderedPDF(buffer.getvalue(), pdf.page)
