"""Rules for editing skill categories. Pure functions: no database."""

from collections.abc import Sequence
from typing import Protocol

from aptum.core.exceptions import AptumError, ConflictError


class CategoryLike(Protocol):
    name: str
    is_system: bool


def check_rename(category: CategoryLike) -> None:
    if category.is_system:
        raise ConflictError(f"The '{category.name}' category cannot be renamed")


def check_delete(category: CategoryLike) -> None:
    if category.is_system:
        raise ConflictError(f"The '{category.name}' category cannot be deleted")


def check_order(ids: Sequence[int], current_ids: Sequence[int]) -> None:
    """The new order must list every existing category exactly once."""
    if len(set(ids)) != len(ids) or set(ids) != set(current_ids):
        raise AptumError("ids must list every skill category exactly once")
