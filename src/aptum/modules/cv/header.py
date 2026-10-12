"""CV header lines, built only from what the user set. Pure functions: no DB, no layout."""

from collections.abc import Iterable

from aptum.common.countries import country_name
from aptum.common.enums import WorkAuthorization, WorkPreference
from aptum.modules.profile.models import Profile

SEPARATOR = " | "


def join_parts(parts: Iterable[str | None]) -> str | None:
    """Non-empty parts joined with the header separator; None when nothing is left."""
    return SEPARATOR.join(part for part in parts if part) or None


def location_line(profile: Profile) -> str | None:
    """`Based in Spain`; None when no country is set."""
    country = country_name(profile.based_in)
    return f"Based in {country}" if country else None


def location_with_timezone(location: str | None, timezone_label: str | None) -> str | None:
    """`Based in Spain (CET)`. The timezone is only printed next to a location."""
    if not location:
        return None
    return f"{location} ({timezone_label})" if timezone_label else location


def work_preference_phrase(preferences: Iterable[str] | None) -> str | None:
    """`Open to remote, hybrid or relocation`. Onsite is the default assumption and is never printed."""
    modes = set(preferences or ())
    options = [mode.value for mode in (WorkPreference.remote, WorkPreference.hybrid, WorkPreference.relocation) if mode in modes]
    if not options:
        return None
    if len(options) == 1:
        return f"Open to {options[0]}"
    return f"Open to {', '.join(options[:-1])} or {options[-1]}"


def authorization_phrase(status: str | None, country: str | None) -> str | None:
    """Only a positive authorization is printed. A sponsorship need never goes on the CV."""
    if status != WorkAuthorization.authorized:
        return None
    return f"Authorized to work in {country}" if country else "Authorized to work"


def availability_line(profile: Profile) -> str | None:
    """`Based in Spain (CET) | Available immediately | Open to remote or relocation | Authorized to work in Spain`."""
    return join_parts((
        location_with_timezone(location_line(profile), profile.timezone_label),
        "Available immediately" if profile.available_immediately else None,
        work_preference_phrase(profile.work_preferences),
        authorization_phrase(profile.work_authorization, country_name(profile.work_authorization_country)),
    ))
