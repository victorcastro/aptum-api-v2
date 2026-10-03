"""Years of experience computed from real experience dates. The only source of "X+ years"
in a generated CV: neither the LLM nor the template may write a different figure."""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date

from aptum.common.enums import ExperienceArea
from aptum.modules.profile.models import Experience


def _month_index(value: date) -> int:
    return value.year * 12 + value.month - 1


def merged_months(periods: Iterable[tuple[date, date]]) -> int:
    """Months covered by the union of [start, end] periods (both months inclusive).
    Overlapping or back-to-back periods count once."""
    spans = sorted((_month_index(start), _month_index(end)) for start, end in periods if end >= start)
    total = 0
    current: list[int] | None = None
    for start, end in spans:
        if current is not None and start <= current[1] + 1:
            current[1] = max(current[1], end)
            continue
        if current is not None:
            total += current[1] - current[0] + 1
        current = [start, end]
    if current is not None:
        total += current[1] - current[0] + 1
    return total


@dataclass(frozen=True)
class YearsOfExperience:
    total_months: int
    by_area_months: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.total_months // 12

    @property
    def by_area(self) -> dict[str, int]:
        return {area: months // 12 for area, months in self.by_area_months.items()}

    def allowed_numbers(self) -> set[int]:
        return {self.total, *self.by_area.values()}


def years_of_experience(experiences: Sequence[Experience], today: date) -> YearsOfExperience:
    """Active experiences only; a current role runs until `today`'s month."""
    periods: list[tuple[date, date, str | None]] = [
        (exp.start_date, exp.end_date or today, exp.area) for exp in experiences if exp.is_active is not False
    ]
    by_area = {
        area.value: months
        for area in ExperienceArea
        if (months := merged_months((s, e) for s, e, a in periods if a == area.value))
    }
    return YearsOfExperience(merged_months((s, e) for s, e, _ in periods), by_area)


_AREA_WORDS = {
    ExperienceArea.ai.value: ("ai", "artificial intelligence", "machine learning", "ml", "llm", "llms", "genai"),
    ExperienceArea.mobile.value: ("mobile", "ios", "android"),
    ExperienceArea.backend.value: ("backend", "back end", "back-end", "server side", "server-side", "api"),
}
YEARS_CLAIM = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.IGNORECASE)


def claim_area(text_after: str) -> str | None:
    """Area a years claim refers to, from the words right after it ("5+ years in mobile")."""
    window = text_after[:60].lower()
    for area, words in _AREA_WORDS.items():
        if any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", window) for word in words):
            return area
    return None


def true_figure(years: YearsOfExperience, area: str | None) -> int:
    """The per-area figure when the claim names an area the profile has tagged experience in
    (even under a year, so "5 years in AI" with 6 months of AI fails), else the total."""
    if area and area in years.by_area_months:
        return years.by_area[area]
    return years.total


def locked_facts_prompt(years: YearsOfExperience) -> str:
    """Block to append to any LLM prompt that writes CV text: the model gets the computed
    figures and is told not to produce any other number of years."""
    lines = [f"- Total professional experience: {years.total} years"]
    lines += [f"- {area} experience: {value} years" for area, value in sorted(years.by_area.items()) if value]
    return (
        "LOCKED FACTS (computed from the candidate's experience dates; copy them exactly):\n"
        + "\n".join(lines)
        + "\nNever state a number of years that is not in this list, never round up, and never"
        " invent employers, titles, dates or metrics that are not in the candidate's profile."
    )
