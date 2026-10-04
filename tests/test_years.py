from datetime import date

from factories import base_profile, experience

from aptum.modules.cv.ats.years import (
    locked_facts_prompt,
    merged_months,
    years_of_experience,
)

TODAY = date(2026, 10, 1)


def test_months_are_inclusive():
    assert merged_months([(date(2023, 1, 1), date(2023, 12, 1))]) == 12


def test_overlapping_periods_count_once():
    periods = [(date(2020, 1, 1), date(2021, 12, 1)), (date(2021, 1, 1), date(2022, 12, 1))]
    assert merged_months(periods) == 36  # not 48


def test_nested_and_adjacent_periods():
    periods = [
        (date(2018, 1, 1), date(2020, 12, 1)),
        (date(2019, 3, 1), date(2019, 6, 1)),  # nested
        (date(2021, 1, 1), date(2021, 6, 1)),  # back-to-back
        (date(2023, 1, 1), date(2023, 1, 1)),  # after a gap
    ]
    assert merged_months(periods) == 36 + 6 + 1


def test_profile_total_and_per_area_with_current_role():
    profile = base_profile()
    for exp, area in zip(profile.experiences, ["ai", "backend", "mobile", None], strict=True):
        exp.area = area
    years = years_of_experience(profile.experiences, TODAY)
    # 2012-01..2015-12 (48) + 2016-02..2019-05 (40) + 2019-06..2026-10 merged (89) = 177 months
    assert years.total_months == 177 and years.total == 14
    assert years.by_area == {"backend": 3, "mobile": 3, "ai": 3}


def test_inactive_experiences_are_ignored():
    active = experience("Dev", "A", date(2020, 1, 1), date(2021, 12, 1), [])
    hidden = experience("Dev", "B", date(2010, 1, 1), date(2019, 12, 1), [], is_active=False)
    assert years_of_experience([active, hidden], TODAY).total == 2


def test_locked_facts_prompt_carries_computed_numbers():
    profile = base_profile()
    profile.experiences[0].area = "ai"
    prompt = locked_facts_prompt(years_of_experience(profile.experiences, TODAY))
    assert "Total professional experience: 14 years" in prompt
    assert "ai experience: 3 years" in prompt
    assert "Never state a number of years" in prompt
