from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


class NumberedCanvas(Canvas):
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
            self.setFillColor("#999999")
            self.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Page {self._pageNumber} of {total}")
            super().showPage()
        super().save()
