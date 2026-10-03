"""Read-only consistency checks on a profile. They never change data, they only report."""

from collections.abc import Sequence
from dataclasses import dataclass

from aptum.common.utils import normalize_name
from aptum.modules.cv.ats.text import normalize_text
from aptum.modules.profile.models import Education

# Words that say nothing about which degree it is.
_DEGREE_STOPWORDS = frozenset({"of", "in", "and", "the", "de", "en", "y", "la", "el", "del", "degree", "program"})


@dataclass(frozen=True)
class DuplicateEducation:
    institution: str
    titles: tuple[str, str]


def _title_tokens(education: Education) -> set[str]:
    text = normalize_text(f"{education.degree} {education.field_of_study or ''}")
    return {token for token in text.split() if token not in _DEGREE_STOPWORDS}


def _titles_overlap(a: Education, b: Education) -> bool:
    """Same title, or one title's words contained in the other, or most words shared."""
    ta, tb = _title_tokens(a), _title_tokens(b)
    if not ta or not tb:
        return False
    if ta <= tb or tb <= ta:
        return True
    return len(ta & tb) / len(ta | tb) >= 0.5


def duplicate_educations(educations: Sequence[Education]) -> list[DuplicateEducation]:
    """Pairs of active entries with the same institution and overlapping titles."""
    active = [e for e in educations if e.is_active is not False]
    duplicates = []
    for i, a in enumerate(active):
        for b in active[i + 1 :]:
            if normalize_name(a.institution) == normalize_name(b.institution) and _titles_overlap(a, b):
                titles = tuple(f"{e.degree}{f', {e.field_of_study}' if e.field_of_study else ''}" for e in (a, b))
                duplicates.append(DuplicateEducation(a.institution, titles))
    return duplicates
