"""Which profile skills go in the CV, in what order, grouped by category.

Only skills that exist in the profile can come out of here: the selection filters and
reorders `profile.skills`, it never adds names.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from aptum.common.enums import SkillCategory
from aptum.modules.cv.ats.text import TextIndex
from aptum.modules.profile.models import ProfileSkill
from aptum.modules.skills.categories import classify_skill, skill_key, skill_terms

MAX_SKILLS = 25


@dataclass(frozen=True)
class SelectedSkill:
    name: str
    category: SkillCategory
    offer_relevant: bool


@dataclass(frozen=True)
class SkillLine:
    category: SkillCategory
    names: tuple[str, ...]

    def render(self) -> str:
        return f"{self.category.value}: {', '.join(self.names)}"


def _category(profile_skill: ProfileSkill) -> SkillCategory:
    if profile_skill.category:
        return SkillCategory(profile_skill.category)
    return classify_skill(profile_skill.skill.name)


def select_skills(
    profile_skills: Sequence[ProfileSkill], offer: str | None = None, limit: int = MAX_SKILLS
) -> list[SelectedSkill]:
    """Without an offer: the first `limit` skills in profile order (`position`).
    With an offer: skills the offer mentions (by name or dictionary alias) first, then the rest,
    each group keeping profile order, cut at `limit`."""
    ordered = sorted(profile_skills, key=lambda ps: (ps.position, ps.id or 0))
    seen: set[str] = set()
    unique: list[ProfileSkill] = []
    for ps in ordered:
        key = skill_key(ps.skill.name)
        if key and key not in seen:
            seen.add(key)
            unique.append(ps)

    index = TextIndex(offer) if offer and offer.strip() else None
    selected = [
        SelectedSkill(
            ps.skill.name,
            _category(ps),
            bool(index and index.find_any(skill_terms(ps.skill.name))),
        )
        for ps in unique
    ]
    if index:
        selected.sort(key=lambda skill: not skill.offer_relevant)  # stable: keeps profile order
    return selected[:limit]


def skill_lines(selected: Sequence[SelectedSkill]) -> list[SkillLine]:
    """One line per category, categories in SkillCategory order, empty ones skipped."""
    return [
        SkillLine(category, names)
        for category in SkillCategory
        if (names := tuple(s.name for s in selected if s.category is category))
    ]
