from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, PlainSerializer, WithJsonSchema

from aptum.common.countries import COUNTRIES


def _parse_year_month(value: object) -> object:
    if isinstance(value, str):
        year, sep, month = value.partition("-")
        if sep and len(year) == 4 and len(month) == 2 and year.isdigit() and month.isdigit():
            return date(int(year), int(month), 1)
        raise ValueError("Expected format YYYY-MM")
    if isinstance(value, date):
        return value.replace(day=1)
    return value


YearMonth = Annotated[
    date,
    BeforeValidator(_parse_year_month),
    PlainSerializer(lambda d: d.strftime("%Y-%m"), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "pattern": r"^\d{4}-(0[1-9]|1[0-2])$", "examples": ["2023-03"]}),
]

def _check_country(value: str) -> str:
    if value not in COUNTRIES:
        raise ValueError("Unknown ISO 3166-1 alpha-2 country code")
    return value


CountryCode = Annotated[
    str,
    Field(pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2"),
    AfterValidator(_check_country),
]
LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{2}$", description="ISO 639-1")]
