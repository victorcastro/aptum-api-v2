from collections.abc import Iterable
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aptum.common.richtext import to_reportlab
from aptum.modules.cv.header import join_parts
from aptum.modules.cv.links import (
    CREDENTIAL_LINK_TEXT,
    LinkEntry,
    format_link_display,
    normalize_link_href,
)


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def rich(text: str, style: ParagraphStyle, bullet: str | None = None) -> Paragraph:
    """User free text with its bold and italic (see `common/richtext.py`)."""
    return Paragraph(to_reportlab(text), style, bulletText=bullet)


def link_markup(label: str, href: str, color: str | None = None) -> str:
    """A real link annotation over plain text."""
    text = escape(label)
    if color:
        text = f'<font color="{color}">{text}</font>'
    return f"<a href={quoteattr(href)}>{text}</a>"


def url_markup(url: str, color: str | None = None) -> str:
    """The clean URL as text (no scheme, no `www.`), linked to the full `https://` URL (project links)."""
    return link_markup(format_link_display(url), normalize_link_href(url), color)


def credential_markup(url: str, color: str | None = None) -> str:
    """`Verify credential`, linked to the credential URL."""
    return link_markup(CREDENTIAL_LINK_TEXT, normalize_link_href(url), color)


def contact_markup(phone: str | None, email: str | None) -> str | None:
    """`phone | email`, the email as a mailto: link."""
    return join_parts((escape(phone) if phone else None, link_markup(email, f"mailto:{email}") if email else None))


def links_markup(links: Iterable[LinkEntry]) -> str | None:
    return join_parts(link_markup(link.label, link.url) for link in links)


def header_paragraphs(
    availability: str | None,
    phone: str | None,
    email: str | None,
    links: Iterable[LinkEntry],
    style: ParagraphStyle,
    links_style: ParagraphStyle | None = None,
) -> list[Paragraph]:
    """Header lines 3-5 (availability, contact, links), one paragraph each; empty lines are left out."""
    lines = [
        (escape(availability) if availability else None, style),
        (contact_markup(phone, email), style),
        (links_markup(links), links_style or style),
    ]
    return [Paragraph(markup, line_style) for markup, line_style in lines if markup]
