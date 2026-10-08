from dataclasses import dataclass
from urllib.parse import urlsplit

from aptum.common.enums import LinkKind
from aptum.modules.profile.models import Profile

# Header print order by kind; links of the same kind keep the order the user saved them in.
_KIND_ORDER = (LinkKind.linkedin, LinkKind.github, LinkKind.portfolio, LinkKind.other)


# Visible text of a certification credential link; the link target is the credential URL.
CREDENTIAL_LINK_TEXT = "Verify credential"


@dataclass(frozen=True)
class LinkEntry:
    label: str
    url: str


def visible_link_urls(profile: Profile) -> list[str]:
    """URLs of the links the user left visible, in the order they saved them, without repeats."""
    urls = (link["url"] for link in profile.links or [] if link.get("visible", True) and link.get("url"))
    return list(dict.fromkeys(urls))


def normalize_link_href(url: str) -> str:
    """Full URL for the link target: `https://` is added when the URL has no scheme."""
    url = url.strip()
    if urlsplit(url).scheme:
        return url
    return f"https://{url.lstrip('/')}"


def format_link_display(url: str) -> str:
    """Visible text of a link: no scheme, no `www.` and no trailing slash on the path.
    Query and fragment are kept. `https://www.linkedin.com/in/x/` -> `linkedin.com/in/x`."""
    parts = urlsplit(normalize_link_href(url))
    host = parts.netloc.removeprefix("www.")
    text = host + parts.path.rstrip("/")
    if parts.query:
        text += f"?{parts.query}"
    if parts.fragment:
        text += f"#{parts.fragment}"
    return text


def _kind_rank(kind: str | None) -> int:
    return _KIND_ORDER.index(kind) if kind in _KIND_ORDER else len(_KIND_ORDER)


def header_links(profile: Profile) -> list[LinkEntry]:
    """Visible links for the CV header: LinkedIn, GitHub, portfolio, then the rest, without repeats.
    The label is the clean URL and the target the full `https://` URL."""
    links = [link for link in profile.links or [] if link.get("visible", True) and link.get("url")]
    hrefs = (normalize_link_href(link["url"]) for link in sorted(links, key=lambda l: _kind_rank(l.get("kind"))))
    return [LinkEntry(format_link_display(href), href) for href in dict.fromkeys(hrefs)]
