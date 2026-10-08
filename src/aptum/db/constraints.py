from enum import StrEnum

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


def in_values_check(column: str, values: type[StrEnum]) -> CheckConstraint:
    """Closed set of string values without a native enum type (cheaper to extend and to roll back)."""
    allowed = ", ".join("'" + value.replace("'", "''") + "'" for value in values)
    return CheckConstraint(f"{column} IS NULL OR {column} IN ({allowed})", name=f"{column}_allowed")


def array_values_check(column: str, values: type[StrEnum]) -> CheckConstraint:
    """Every element of a string array belongs to a closed set (see `in_values_check`)."""
    allowed = ", ".join("'" + value.replace("'", "''") + "'" for value in values)
    return CheckConstraint(f"{column} <@ ARRAY[{allowed}]::varchar[]", name=f"{column}_allowed")
