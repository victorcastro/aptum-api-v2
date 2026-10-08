from io import BytesIO
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from aptum.modules.cv.document import CVDocument
from aptum.modules.cv.templates.common import header_paragraphs, p

_INK = "#1F2933"
_ACCENT = "#1F3A5F"
_GRAY = "#52606D"
_RULE = "#B8C2CC"


def _labeled(label: str, value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"<b>{escape(label)}:</b> {escape(value)}", style)


class _DatedLine(Flowable):
    """Title wrapped on the left, date on the first line at the right margin. One atomic flowable, so
    the block never splits across pages, and the date never wraps: the title gets the width left over."""

    _GAP = 8

    def __init__(self, title: str, dates: str, title_style: ParagraphStyle, date_style: ParagraphStyle) -> None:
        super().__init__()
        self._title = p(title, title_style)
        self._title_style = title_style
        self._date_style = date_style
        self._dates = dates
        self._date_width = stringWidth(dates, date_style.fontName, date_style.fontSize) if dates else 0

    def wrap(self, availWidth: float, availHeight: float) -> tuple[float, float]:
        reserved = self._date_width + self._GAP if self._dates else 0
        _, height = self._title.wrap(availWidth - reserved, availHeight)
        self.width = availWidth
        self.height = height
        return availWidth, height

    def getSpaceBefore(self) -> float:
        return self._title.getSpaceBefore()

    def getSpaceAfter(self) -> float:
        return self._title.getSpaceAfter()

    def draw(self) -> None:
        self._title.drawOn(self.canv, 0, 0)
        if self._dates:
            style = self._date_style
            baseline = self.height - getattr(self._title.blPara, "ascent", self._title_style.fontSize)
            self.canv.setFont(style.fontName, style.fontSize)
            self.canv.setFillColor(style.textColor)
            self.canv.drawRightString(self.width, baseline, self._dates)


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
        story.extend(header_paragraphs(doc.availability_line, doc.phone, doc.email, doc.links, contact, links))
        story.append(Spacer(1, 0.4 * cm))

        def heading(title: str) -> None:
            story.append(p(title.upper(), section))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor(_RULE), spaceBefore=1, spaceAfter=4))

        if doc.summary:
            heading("Summary")
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
                story.append(_DatedLine(exp.title, exp.dates, item, muted))
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
                if project.url:
                    story.append(
                        Paragraph(
                            f"<a href={quoteattr(project.url)}><font color=\"{_ACCENT}\">{escape(project.url)}</font></a>",
                            body,
                        )
                    )

        if doc.educations:
            heading("Education")
            for edu in doc.educations:
                story.append(_DatedLine(edu.title, edu.dates, item, muted))
                story.append(p(edu.institution, body))

        if doc.certifications:
            heading("Certifications")
            for cert in doc.certifications:
                story.append(_DatedLine(cert.title, cert.dates, item, muted))
                markup = escape(cert.issuer)
                if cert.url:
                    markup += f" | <a href={quoteattr(cert.url)}><font color=\"{_ACCENT}\">{escape(cert.url)}</font></a>"
                story.append(Paragraph(markup, body))

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
