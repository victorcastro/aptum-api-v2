"""Rules for a profile's skill categories. Pure functions: no database."""

from collections.abc import Sequence

from aptum.core.exceptions import AptumError


def check_order(ids: Sequence[int], current_ids: Sequence[int]) -> None:
    """The new order must list every category of the profile exactly once."""
    if len(set(ids)) != len(ids) or set(ids) != set(current_ids):
        raise AptumError("ids must list every skill category exactly once")
