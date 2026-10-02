from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)
