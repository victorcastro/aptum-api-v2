"""Which profile skills go in the CV, in what order, grouped by category.

Only skills that exist in the profile can come out of here: the selection filters and
reorders `profile.skills`, it never adds names.

Order is by evidence, never by a manual position:
1. mentioned by the job offer (name or dictionary alias), when there is one;
2. used in the most recent experience (experience skills; a current role counts as today);
3. higher `level`, then more `years_experience`;
4. alphabetical.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from aptum.common.enums import SkillLevel
from aptum.modules.cv.ats.text import TextIndex
from aptum.modules.profile.models import Experience, ProfileSkill
from aptum.modules.skill_categories.models import SkillCategory, print_name, print_order
from aptum.modules.skills.categories import skill_key, skill_terms

MAX_SKILLS = 25


@dataclass(frozen=True)
class SelectedSkill:
    name: str
    category: SkillCategory | None
    offer_relevant: bool


@dataclass(frozen=True)
class SkillLine:
    category: str
    names: tuple[str, ...]

    def render(self) -> str:
        return f"{self.category}: {', '.join(self.names)}"


_LEVEL_RANK = {SkillLevel.expert: 4, SkillLevel.advanced: 3, SkillLevel.intermediate: 2, SkillLevel.beginner: 1}


def last_used(experiences: Sequence[Experience]) -> dict[str, date]:
    """Skill key -> end of the most recent active experience that lists it (current = date.max)."""
    result: dict[str, date] = {}
    for exp in experiences:
        if exp.is_active is False:
            continue
        end = exp.end_date or date.max
        for skill in exp.skills:
            key = skill_key(skill.name)
            if key and end > result.get(key, date.min):
                result[key] = end
    return result


def select_skills(
    profile_skills: Sequence[ProfileSkill],
    offer: str | None = None,
    experiences: Sequence[Experience] = (),
    limit: int = MAX_SKILLS,
) -> list[SelectedSkill]:
    """Up to `limit` profile skills ordered by evidence (see module docstring)."""
    used = last_used(experiences)
    index = TextIndex(offer) if offer and offer.strip() else None

    def evidence(ps: ProfileSkill) -> tuple:
        key = skill_key(ps.skill.name)
        relevant = bool(index and index.find_any(skill_terms(ps.skill.name)))
        recency = used.get(key)
        return (
            not relevant,
            recency is None,
            -(recency.toordinal() if recency else 0),
            -_LEVEL_RANK.get(SkillLevel(ps.level), 0) if ps.level else 0,
            -(ps.years_experience or 0),
            ps.skill.name.casefold(),
            ps.id or 0,
        )

    seen: set[str] = set()
    selected: list[SelectedSkill] = []
    for ps in sorted(profile_skills, key=evidence):
        key = skill_key(ps.skill.name)
        if key and key not in seen:
            seen.add(key)
            selected.append(SelectedSkill(ps.skill.name, ps.category, not evidence(ps)[0]))
    return selected[:limit]


def skill_lines(selected: Sequence[SelectedSkill]) -> list[SkillLine]:
    """One line per category, categories in `position` order and `Other` last."""
    groups: dict[int | None, tuple[SkillCategory | None, list[str]]] = {}
    for skill in selected:
        key = skill.category.id if skill.category else None
        groups.setdefault(key, (skill.category, []))[1].append(skill.name)
    ordered = sorted(groups.values(), key=lambda group: print_order(group[0]))
    return [SkillLine(print_name(category), tuple(names)) for category, names in ordered]
