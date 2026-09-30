from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from aptum.modules.cv.document import CVDocument


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


class _NumberedCanvas(Canvas):
    """Two-pass canvas: pages are buffered so the footer can print "Page X of N"."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_pages: list[dict] = []

    def showPage(self) -> None:
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self.setFont("Helvetica", 8)
            self.setFillColor("#555555")
            self.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Page {self._pageNumber} of {total}")
            super().showPage()
        super().save()


class ClassicTemplate:
    def render(self, doc: CVDocument) -> bytes:
        base = getSampleStyleSheet()
        name_style = ParagraphStyle("Name", parent=base["Title"], alignment=0, spaceAfter=2)
        section = ParagraphStyle("Section", parent=base["Heading2"], spaceBefore=12, spaceAfter=4)
        item = ParagraphStyle("Item", parent=base["Heading4"], spaceBefore=6, spaceAfter=0)
        body = base["BodyText"]
        muted = ParagraphStyle("Muted", parent=body, textColor="#555555")
        bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=0)

        story: list = [_p(doc.full_name, name_style)]
        if doc.headline:
            story.append(_p(doc.headline, body))
        if doc.contact_line:
            story.append(_p(doc.contact_line, muted))
        if doc.links_line:
            story.append(_p(doc.links_line, muted))

        if doc.summary:
            story.append(_p("Summary", section))
            story.append(_p(doc.summary, body))

        if doc.experiences:
            story.append(_p("Experience", section))
            for exp in doc.experiences:
                story.append(_p(exp.title, item))
                story.append(_p(exp.dates, muted))
                if exp.description:
                    story.append(_p(exp.description, body))
                for text in exp.bullets:
                    story.append(Paragraph(escape(text), bullet, bulletText="•"))
                if exp.skills_line:
                    story.append(_p("Skills: " + exp.skills_line, muted))

        if doc.educations:
            story.append(_p("Education", section))
            for edu in doc.educations:
                story.append(_p(edu.title, item))
                story.append(_p(edu.dates, muted))
                if edu.description:
                    story.append(_p(edu.description, body))

        if doc.skills_line:
            story.append(_p("Skills", section))
            story.append(_p(doc.skills_line, body))

        if doc.languages_line:
            story.append(_p("Languages", section))
            story.append(_p(doc.languages_line, body))

        if doc.certifications:
            story.append(_p("Certifications", section))
            for cert in doc.certifications:
                story.append(_p(cert.title, item))
                story.append(_p(cert.dates, muted))

        if doc.projects:
            story.append(_p("Projects", section))
            for project in doc.projects:
                story.append(_p(project.name, item))
                if project.description:
                    story.append(_p(project.description, body))

        story.append(Spacer(1, 0.2 * cm))
        buffer = BytesIO()
        SimpleDocTemplate(
            buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm
        ).build(story, canvasmaker=_NumberedCanvas)
        return buffer.getvalue()
