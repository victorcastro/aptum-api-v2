from datetime import date

import pytest
from conftest import pdf_text
from factories import base_profile
from pydantic import ValidationError

from aptum.modules.cv.ats.pipeline import generate_ats_cv
from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.links import visible_link_urls
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate
from aptum.modules.profile.schemas import MAX_LINKS, ProfileUpdate

GITHUB = "https://github.com/example-alex"
LINKEDIN = "https://www.linkedin.com/in/example-alex"


def _link(kind, url, visible=True):
    return {"kind": kind, "url": url, "visible": visible}


def test_hidden_link_is_left_out_of_both_cv_templates():
    profile = base_profile(links=[_link("linkedin", LINKEDIN), _link("github", GITHUB, visible=False)])
    assert visible_link_urls(profile) == [LINKEDIN]
    assert GITHUB not in pdf_text(SoftwareEngineerTemplate().render(build_cv_data(profile)))
    assert GITHUB not in pdf_text(generate_ats_cv(profile, today=date(2026, 10, 1)).pdf)


def test_no_links_or_all_hidden_prints_no_links_line():
    for links in ([], [_link("github", GITHUB, visible=False)]):
        assert visible_link_urls(base_profile(links=links)) == []


def test_visible_defaults_to_true_and_repeated_urls_print_once():
    profile = base_profile(links=[{"kind": "github", "url": GITHUB}, _link("other", GITHUB)])
    assert visible_link_urls(profile) == [GITHUB]


def test_update_accepts_links_and_dumps_plain_dicts():
    data = ProfileUpdate(links=[_link("linkedin", LINKEDIN), _link("other", "https://medium.com/@alex")])
    dumped = data.model_dump(exclude_unset=True)["links"]
    assert dumped[0]["url"] == LINKEDIN and dumped[0]["visible"] is True


@pytest.mark.parametrize(
    "links",
    [
        [_link("linkedin", GITHUB)],
        [_link("github", LINKEDIN)],
        [_link("linkedin", LINKEDIN), _link("linkedin", LINKEDIN)],
        [_link("other", "javascript:alert(1)")],
        [_link("other", f"https://example.com/{i}") for i in range(MAX_LINKS + 1)],
    ],
)
def test_update_rejects_bad_links(links):
    with pytest.raises(ValidationError):
        ProfileUpdate(links=links)


def test_update_rejects_null_links():
    with pytest.raises(ValidationError):
        ProfileUpdate(links=None)
