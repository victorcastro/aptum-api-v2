"""CV header lines, built only from what the user set. Pure functions: no DB, no layout."""

from collections.abc import Iterable

from aptum.common.countries import country_name
from aptum.common.enums import WorkAuthorization, WorkMode
from aptum.modules.profile.models import Profile

SEPARATOR = " | "


def join_parts(parts: Iterable[str | None]) -> str | None:
    """Non-empty parts joined with the header separator; None when nothing is left."""
    return SEPARATOR.join(part for part in parts if part) or None


def location_line(profile: Profile) -> str:
    return ", ".join(x for x in (profile.city, country_name(profile.country_code)) if x)


def location_with_timezone(location: str | None, timezone_label: str | None) -> str | None:
    """`Madrid, Spain (CET)`. The timezone is only printed next to a location."""
    if not location:
        return None
    return f"{location} ({timezone_label})" if timezone_label else location


def work_preference_phrase(preferences: Iterable[str] | None) -> str | None:
    """Remote and hybrid are printed; onsite is the default assumption and is never printed."""
    modes = set(preferences or ())
    remote, hybrid = WorkMode.remote in modes, WorkMode.hybrid in modes
    if remote and hybrid:
        return "Open to remote or hybrid"
    if remote:
        return "Open to remote"
    if hybrid:
        return "Open to hybrid"
    return None


def authorization_phrase(status: str | None, country: str | None) -> str | None:
    """Only a positive authorization is printed. A sponsorship need never goes on the CV."""
    if status != WorkAuthorization.authorized:
        return None
    return f"Authorized to work in {country}" if country else "Authorized to work"


def availability_line(profile: Profile) -> str | None:
    """`Madrid, Spain (CET) | Open to remote | Authorized to work in Spain | Open to relocation`."""
    return join_parts((
        location_with_timezone(location_line(profile), profile.timezone_label),
        work_preference_phrase(profile.work_preferences),
        authorization_phrase(profile.work_authorization, country_name(profile.work_authorization_country)),
        "Open to relocation" if profile.open_to_relocation else None,
    ))
