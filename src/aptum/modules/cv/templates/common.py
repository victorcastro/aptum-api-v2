from collections.abc import Iterable
from xml.sax.saxutils import escape, quoteattr

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from aptum.modules.cv.header import join_parts
from aptum.modules.cv.links import LinkEntry, format_link_display, normalize_link_href


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def link_markup(label: str, href: str) -> str:
    """A real link annotation over plain text."""
    return f"<a href={quoteattr(href)}>{escape(label)}</a>"


def url_markup(url: str, color: str | None = None, *, clean: bool = True) -> str:
    """A link to `url` with its full `https://` target. The text is the clean URL
    (`credly.com/badges/x`), or the full one with `clean=False` (project links)."""
    href = normalize_link_href(url)
    label = escape(format_link_display(url) if clean else href)
    if color:
        label = f'<font color="{color}">{label}</font>'
    return f"<a href={quoteattr(href)}>{label}</a>"


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
