import pytest
from factories import base_profile
from pydantic import ValidationError

from aptum.modules.cv.header import (
    authorization_phrase,
    availability_line,
    location_with_timezone,
    work_preference_phrase,
)
from aptum.modules.cv.links import (
    format_link_display,
    header_links,
    normalize_link_href,
)
from aptum.modules.profile.schemas import ProfileUpdate


@pytest.mark.parametrize(
    ("preferences", "expected"),
    [
        (None, None),
        ([], None),
        (["onsite"], None),
        (["remote"], "Open to remote"),
        (["hybrid"], "Open to hybrid"),
        (["remote", "hybrid"], "Open to remote or hybrid"),
        (["hybrid", "remote"], "Open to remote or hybrid"),
        (["remote", "onsite"], "Open to remote"),
        (["hybrid", "onsite"], "Open to hybrid"),
        (["remote", "hybrid", "onsite"], "Open to remote or hybrid"),
        (["relocation"], "Open to relocation"),
        (["onsite", "relocation"], "Open to relocation"),
        (["remote", "relocation"], "Open to remote or relocation"),
        (["hybrid", "relocation"], "Open to hybrid or relocation"),
        (["relocation", "hybrid", "remote"], "Open to remote, hybrid or relocation"),
    ],
)
def test_work_preference_phrase(preferences, expected):
    assert work_preference_phrase(preferences) == expected


@pytest.mark.parametrize(
    ("status", "country", "expected"),
    [
        ("authorized", "Spain", "Authorized to work in Spain"),
        ("authorized", None, "Authorized to work"),
        ("authorized", "", "Authorized to work"),
        ("requires_sponsorship", "Spain", None),
        ("requires_sponsorship", None, None),
        (None, "Spain", None),
        (None, None, None),
    ],
)
def test_authorization_phrase(status, country, expected):
    assert authorization_phrase(status, country) == expected


@pytest.mark.parametrize(
    ("location", "timezone", "expected"),
    [
        ("Based in Spain", "CET", "Based in Spain (CET)"),
        ("Based in Spain", None, "Based in Spain"),
        ("", "CET", None),
        (None, None, None),
    ],
)
def test_location_with_timezone(location, timezone, expected):
    assert location_with_timezone(location, timezone) == expected


def _profile(**fields):
    defaults = {
        "based_in": "ES",
        "timezone_label": None,
        "work_preferences": [],
        "available_immediately": False,
        "work_authorization": None,
        "work_authorization_country": None,
    }
    return base_profile(**{**defaults, **fields})


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        (
            {"timezone_label": "CET", "work_preferences": ["remote", "relocation"], "work_authorization": "authorized",
             "work_authorization_country": "ES"},
            "Based in Spain (CET) | Open to remote or relocation | Authorized to work in Spain",
        ),
        (
            {"timezone_label": "CET", "work_preferences": ["remote"], "work_authorization": "authorized",
             "work_authorization_country": "ES"},
            "Based in Spain (CET) | Open to remote | Authorized to work in Spain",
        ),
        ({}, "Based in Spain"),
        (
            {"timezone_label": "CET", "available_immediately": True, "work_preferences": ["remote"]},
            "Based in Spain (CET) | Available immediately | Open to remote",
        ),
        ({"based_in": None, "available_immediately": True}, "Available immediately"),
        ({"work_authorization": "authorized"}, "Based in Spain | Authorized to work"),
        ({"work_authorization": "requires_sponsorship", "work_authorization_country": "ES"}, "Based in Spain"),
        (
            {"work_authorization": "requires_sponsorship", "work_preferences": ["relocation"]},
            "Based in Spain | Open to relocation",
        ),
        ({"work_preferences": ["onsite", "relocation"]}, "Based in Spain | Open to relocation"),
        ({"work_preferences": ["hybrid", "remote"]}, "Based in Spain | Open to remote or hybrid"),
        (
            {"based_in": None, "timezone_label": "CET", "work_preferences": ["hybrid"]},
            "Open to hybrid",
        ),
        (
            {"based_in": None, "work_authorization": "authorized",
             "work_authorization_country": "ES", "work_preferences": ["relocation"]},
            "Open to relocation | Authorized to work in Spain",
        ),
        ({"based_in": None, "timezone_label": "CET"}, None),
        ({"based_in": None, "work_authorization": "requires_sponsorship"}, None),
        ({"based_in": None, "work_preferences": None}, None),
    ],
)
def test_availability_line(fields, expected):
    line = availability_line(_profile(**fields))
    assert line == expected
    if line:
        assert not line.startswith(" |") and not line.endswith("| ") and "|  |" not in line


@pytest.mark.parametrize(
    ("url", "display"),
    [
        ("https://www.linkedin.com/in/hugocastroc/", "linkedin.com/in/hugocastroc"),
        ("https://www.linkedin.com/in/test/", "linkedin.com/in/test"),
        ("https://github.com/test", "github.com/test"),
        ("https://victorcastro.dev", "victorcastro.dev"),
        ("https://victorcastro.dev/", "victorcastro.dev"),
        ("http://www.example.com/blog/", "example.com/blog"),
        ("www.example.com/blog", "example.com/blog"),
        ("example.com", "example.com"),
        ("https://medium.com/@alex/post?utm=1&x=2", "medium.com/@alex/post?utm=1&x=2"),
        ("https://example.com/path/?q=1", "example.com/path?q=1"),
        ("https://example.com/page#top", "example.com/page#top"),
    ],
)
def test_format_link_display(url, display):
    assert format_link_display(url) == display


@pytest.mark.parametrize(
    ("url", "href"),
    [
        ("https://www.linkedin.com/in/test/", "https://www.linkedin.com/in/test/"),
        ("http://example.com", "http://example.com"),
        ("www.example.com/blog", "https://www.example.com/blog"),
        ("example.com/?q=1", "https://example.com/?q=1"),
        ("  github.com/test ", "https://github.com/test"),
    ],
)
def test_normalize_link_href(url, href):
    assert normalize_link_href(url) == href


def _link(kind: str, url: str, visible: bool = True) -> dict:
    return {"kind": kind, "label": kind, "url": url, "visible": visible}


def test_header_links_go_linkedin_github_portfolio_then_others_in_saved_order():
    profile = base_profile(links=[
        _link("other", "https://medium.com/@alex"),
        _link("portfolio", "https://alex.dev/"),
        _link("github", "https://github.com/alex"),
        _link("other", "https://dev.to/alex"),
        _link("linkedin", "https://www.linkedin.com/in/alex/"),
        _link("other", "https://hidden.example.com", visible=False),
    ])
    assert [(link.label, link.url) for link in header_links(profile)] == [
        ("linkedin.com/in/alex", "https://www.linkedin.com/in/alex/"),
        ("github.com/alex", "https://github.com/alex"),
        ("alex.dev", "https://alex.dev/"),
        ("medium.com/@alex", "https://medium.com/@alex"),
        ("dev.to/alex", "https://dev.to/alex"),
    ]


def test_profile_update_accepts_work_preferences_and_timezone_label():
    data = ProfileUpdate(work_preferences=["remote", "hybrid", "remote"], timezone_label="  CET ")
    assert data.model_dump(exclude_unset=True) == {"work_preferences": ["remote", "hybrid"], "timezone_label": "CET"}
    assert ProfileUpdate(timezone_label="").timezone_label is None
    assert ProfileUpdate(work_preferences=[]).work_preferences == []


@pytest.mark.parametrize(
    "body",
    [{"work_preferences": ["anywhere"]}, {"work_preferences": None}, {"timezone_label": "X" * 17}],
)
def test_profile_update_rejects_bad_values(body):
    with pytest.raises(ValidationError):
        ProfileUpdate(**body)
