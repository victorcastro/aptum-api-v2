"""Fidelity check, in code: every employer, job title, date and number in the generated CV
must exist in the profile (normalized comparison). No LLM is involved.

On a mismatch the offending part is repaired once: structured fields are regenerated from the
profile row they came from, free text with an unknown number is removed. Whatever still fails
after that single pass is returned as a fidelity issue."""

import re
from dataclasses import dataclass
from datetime import date

from aptum.common.utils import normalize_name
from aptum.modules.cv.ats.document import ATSDocument, ATSExperience, format_month
from aptum.modules.cv.ats.report import CVWarning
from aptum.modules.cv.ats.years import YearsOfExperience
from aptum.modules.profile.models import Profile

_NUMBER = re.compile(r"(?<![A-Za-z0-9.,])(\d+(?:[.,]\d+)*)(?=[xXkKmM]\b|%|(?![A-Za-z0-9]))")
_MONTH_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})\b")


def normalize_number(raw: str) -> str:
    """'12,000' -> '12000', '4.50' -> '4.5'. A comma followed by 1-2 digits is a decimal comma."""
    if re.fullmatch(r"\d{1,3}(,\d{3})+", raw):
        raw = raw.replace(",", "")
    raw = raw.replace(",", ".")
    if "." in raw:
        raw = raw.rstrip("0").rstrip(".")
    return raw.lstrip("0") or "0"


def numbers_in(text: str) -> list[str]:
    return [normalize_number(match.group(1)) for match in _NUMBER.finditer(text)]


def profile_text_blocks(profile: Profile) -> list[str]:
    """All user-entered free text of a profile."""
    blocks = [profile.headline, profile.summary]
    for exp in profile.experiences:
        blocks += [exp.position, exp.description, *(f.description for f in exp.functions)]
        blocks += [skill.name for skill in exp.skills]
    for edu in profile.educations:
        blocks += [edu.degree, edu.field_of_study, edu.institution, edu.grade, edu.description]
    for cert in profile.certifications:
        blocks += [cert.name, cert.issuing_organization]
    for project in profile.projects:
        blocks += [project.name, project.description]
    blocks += [ps.skill.name for ps in profile.skills]
    return [block for block in blocks if block]


def _profile_dates(profile: Profile) -> list[date]:
    dates = [d for exp in profile.experiences for d in (exp.start_date, exp.end_date)]
    dates += [d for edu in profile.educations for d in (edu.start_date, edu.end_date)]
    dates += [d for cert in profile.certifications for d in (cert.issue_date, cert.expiration_date)]
    dates += [d for project in profile.projects for d in (project.start_date, project.end_date)]
    return [d for d in dates if d]


@dataclass(frozen=True)
class ProfileFacts:
    employers: frozenset[str]
    titles: frozenset[str]
    months: frozenset[str]
    numbers: frozenset[str]


def profile_facts(profile: Profile, years: YearsOfExperience) -> ProfileFacts:
    employers = {normalize_name(c.name) for exp in profile.experiences for c in (exp.employer, exp.client) if c}
    dates = _profile_dates(profile)
    numbers = {n for block in profile_text_blocks(profile) for n in numbers_in(block)}
    numbers |= {str(d.year) for d in dates}
    numbers |= {str(y) for edu in profile.educations for y in (edu.start_year, edu.end_year) if y}
    numbers |= {str(value) for value in years.allowed_numbers()}  # computed from the profile's dates
    return ProfileFacts(
        employers=frozenset(employers),
        titles=frozenset(normalize_name(exp.position) for exp in profile.experiences),
        months=frozenset(format_month(d) for d in dates),
        numbers=frozenset(numbers),
    )


@dataclass(frozen=True)
class FidelityIssue:
    kind: str  # employer | title | date | number
    value: str
    location: str
    message: str


def _experience_issues(exp: ATSExperience, facts: ProfileFacts) -> list[FidelityIssue]:
    issues = []
    for company in (exp.employer, exp.client):
        if company and normalize_name(company) not in facts.employers:
            issues.append(FidelityIssue("employer", company, exp.title, "Employer not found in the profile."))
    if normalize_name(exp.position) not in facts.titles:
        issues.append(FidelityIssue("title", exp.position, exp.title, "Job title not found in the profile."))
    for value in (exp.start, exp.end):
        if value and format_month(value) not in facts.months:
            issues.append(FidelityIssue("date", format_month(value), exp.title, "Date not found in the profile."))
    return issues


def _text_issues(location: str, text: str, facts: ProfileFacts) -> list[FidelityIssue]:
    issues = [
        FidelityIssue("number", number, location, "Number not found in the profile.")
        for number in dict.fromkeys(numbers_in(text))
        if number not in facts.numbers
    ]
    issues += [
        FidelityIssue("date", match.group(0), location, "Date not found in the profile.")
        for match in _MONTH_DATE.finditer(text)
        if match.group(0) not in facts.months
    ]
    return issues


def check_fidelity(doc: ATSDocument, facts: ProfileFacts) -> list[FidelityIssue]:
    issues: list[FidelityIssue] = []
    for exp in doc.experiences:
        issues += _experience_issues(exp, facts)
    for location, text in doc.text_blocks():
        issues += _text_issues(location, text, facts)
    for edu in doc.educations:
        issues += _text_issues("education", edu.dates, facts)
    for cert in doc.certifications:
        issues += _text_issues("certifications", cert.dates, facts)
    return issues


def _bad(text: str | None, facts: ProfileFacts) -> bool:
    return bool(text) and bool(_text_issues("", text, facts))


def _repair(doc: ATSDocument, profile: Profile, facts: ProfileFacts, warnings: list[CVWarning]) -> None:
    sources = {exp.id: exp for exp in profile.experiences}

    if _bad(doc.headline, facts):
        doc.headline = profile.headline or None
    if _bad(doc.summary, facts):
        sentences = re.split(r"(?<=[.!?])\s+", doc.summary)
        kept = [s for s in sentences if not _bad(s, facts)]
        for sentence in sentences:
            if sentence not in kept:
                warnings.append(CVWarning("fidelity_removed", "Removed: not supported by the profile.",
                                          section="summary", text=sentence))
        doc.summary = " ".join(kept) or None

    for exp in doc.experiences:
        source = sources.get(exp.experience_id)
        if source is not None and _experience_issues(exp, facts):
            exp.position = source.position
            exp.employer = source.employer.name
            exp.client = source.client.name if source.client else None
            exp.start, exp.end, exp.current = source.start_date, source.end_date, source.end_date is None
            warnings.append(CVWarning("fidelity_restored", "Role header restored from the profile.",
                                      section="experience", item=exp.title))
        if _bad(exp.description, facts):
            exp.description = None
        for bullet in [b for b in exp.bullets if _bad(b, facts)]:
            exp.bullets.remove(bullet)
            warnings.append(CVWarning("fidelity_removed", "Removed: not supported by the profile.",
                                      section="experience", item=exp.title, text=bullet))

    for project in doc.projects:
        if _bad(project.description, facts):
            project.description = None


def enforce_fidelity(
    doc: ATSDocument, profile: Profile, facts: ProfileFacts, warnings: list[CVWarning]
) -> list[FidelityIssue]:
    """Check, repair once, check again; return what still fails."""
    if not check_fidelity(doc, facts):
        return []
    _repair(doc, profile, facts, warnings)
    return check_fidelity(doc, facts)
