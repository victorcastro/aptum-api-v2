from sqlalchemy import CheckConstraint


def month_precision_checks(*columns: str) -> tuple[CheckConstraint, ...]:
    """CV dates are month/year only: stored as a date pinned to the first day of the month."""
    return tuple(
        CheckConstraint(
            f"{column} IS NULL OR EXTRACT(day FROM {column}) = 1",
            name=f"{column}_first_day",
        )
        for column in columns
    )


def date_range_check(start: str = "start_date", end: str = "end_date") -> CheckConstraint:
    return CheckConstraint(
        f"{start} IS NULL OR {end} IS NULL OR {end} >= {start}",
        name="date_range",
    )
