import pytest

from aptum.core.exceptions import AptumError
from aptum.modules.skill_categories.policy import check_order


def test_order_must_be_a_permutation_of_the_profiles_ids():
    check_order([3, 1, 2], [1, 2, 3])


@pytest.mark.parametrize("ids", [[1, 2], [1, 2, 3, 4], [1, 1, 2], [1, 2, 9], []])
def test_order_missing_extra_repeated_or_unknown_ids_is_400(ids):
    with pytest.raises(AptumError, match="every skill category exactly once"):
        check_order(ids, [1, 2, 3])
