from types import SimpleNamespace

import pytest

from aptum.core.exceptions import AptumError, ConflictError
from aptum.modules.commons.policy import canonical_level, clean_degree_name, place


def degree(id, name, level):
    return SimpleNamespace(id=id, name=name, level=level)


CATALOG = [degree(1, "Technical Diploma", "Technical"), degree(2, "Bachelor of Science", "Undergraduate"), degree(3, "PhD", "Doctoral")]


def test_name_is_trimmed():
    assert clean_degree_name("  Bootcamp Certificate ", CATALOG) == "Bootcamp Certificate"


@pytest.mark.parametrize("name", ["", "   ", "--", "!!"])
def test_name_needs_letters_or_numbers(name):
    with pytest.raises(AptumError):
        clean_degree_name(name, CATALOG)


def test_duplicate_name_ignores_case_accents_and_spaces():
    with pytest.raises(ConflictError):
        clean_degree_name("  bachelor  of SCIÉNCE", CATALOG)


def test_a_degree_may_keep_its_own_name():
    assert clean_degree_name("PhD", CATALOG, own_id=3) == "PhD"


def test_level_reuses_the_existing_spelling():
    assert canonical_level(" undergraduate ", ["Technical", "Undergraduate"]) == "Undergraduate"
    assert canonical_level("Certificates", ["Technical"]) == "Certificates"


def test_level_needs_letters_or_numbers():
    with pytest.raises(AptumError):
        canonical_level("  ", ["Technical"])


def test_place_goes_after_the_last_degree_of_its_level():
    new = degree(None, "Bachelor of Arts", "Undergraduate")
    assert [d.name for d in place(CATALOG, new)] == ["Technical Diploma", "Bachelor of Science", "Bachelor of Arts", "PhD"]


def test_place_puts_a_new_level_at_the_end():
    new = degree(None, "Bootcamp", "Other")
    assert place(CATALOG, new)[-1] is new
