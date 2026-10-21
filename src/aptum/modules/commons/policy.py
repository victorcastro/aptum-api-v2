"""Rules for the degree catalog. Pure functions: no database."""

from collections.abc import Iterable, Sequence
from typing import Protocol

from aptum.common.utils import normalize_name, slugify
from aptum.core.exceptions import AptumError, ConflictError


class DegreeLike(Protocol):
    id: int | None
    name: str
    level: str


def clean_degree_name(name: str, others: Iterable[DegreeLike], own_id: int | None = None) -> str:
    """Trimmed name, or 400 without letters or numbers, or 409 when another degree has the same normalized name."""
    name = name.strip()
    if not slugify(name):
        raise AptumError("Degree name must contain letters or numbers")
    for other in others:
        if other.id != own_id and normalize_name(other.name) == normalize_name(name):
            raise ConflictError("A degree with that name already exists")
    return name


def canonical_level(level: str, existing: Iterable[str]) -> str:
    """The spelling an existing level already uses when `level` matches one ignoring case and accents."""
    level = level.strip()
    if not slugify(level):
        raise AptumError("Degree level must contain letters or numbers")
    for known in existing:
        if normalize_name(known) == normalize_name(level):
            return known
    return level


def place[D: DegreeLike](others: Sequence[D], moved: D) -> list[D]:
    """`others` (catalog order, without `moved`) with `moved` right after the last degree of its level,
    or at the end when the level is new."""
    position = max((index + 1 for index, degree in enumerate(others) if degree.level == moved.level), default=len(others))
    return [*others[:position], moved, *others[position:]]
