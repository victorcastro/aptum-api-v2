import pytest

from aptum.core.exceptions import AptumError, ConflictError
from aptum.modules.skill_categories.models import SkillCategory
from aptum.modules.skill_categories.policy import (
    check_delete,
    check_order,
    check_rename,
)

BACKEND = SkillCategory(id=2, name="Backend", position=2, is_system=False)
OTHER = SkillCategory(id=6, name="Other", position=6, is_system=True)


def test_a_regular_category_can_be_renamed_and_deleted():
    check_rename(BACKEND)
    check_delete(BACKEND)


def test_the_system_category_cannot_be_renamed_or_deleted():
    with pytest.raises(ConflictError, match="cannot be renamed"):
        check_rename(OTHER)
    with pytest.raises(ConflictError, match="cannot be deleted"):
        check_delete(OTHER)


def test_order_must_be_a_permutation_of_the_existing_ids():
    check_order([3, 1, 2], [1, 2, 3])


@pytest.mark.parametrize("ids", [[1, 2], [1, 2, 3, 4], [1, 1, 2], [1, 2, 9], []])
def test_order_missing_extra_repeated_or_unknown_ids_is_400(ids):
    with pytest.raises(AptumError, match="every skill category exactly once"):
        check_order(ids, [1, 2, 3])
