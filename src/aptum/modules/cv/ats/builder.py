"""Profile -> ATSDocument. Every value comes from the profile; nothing is generated here."""

from aptum.common.constants import LANGUAGE_NAMES
from aptum.common.countries import country_name
from aptum.common.enums import (
    EnglishLevel,
    LanguageProficiency,
    LinkKind,
    WorkAuthorization,
)
from aptum.modules.cv.ats.document import (
    ATSCertification,
    ATSDocument,
    ATSEducation,
    ATSExperience,
    ATSProject,
    format_range,
    format_year_range,
)
from aptum.modules.cv.ats.skills import select_skills, skill_lines
from aptum.modules.profile.models import Education, Profile

_PROFICIENCY_LABELS = {
    LanguageProficiency.elementary: "Elementary proficiency",
    LanguageProficiency.limited_working: "Limited working proficiency",
    LanguageProficiency.professional_working: "Professional working proficiency",
    LanguageProficiency.full_professional: "Full professional proficiency",
    LanguageProficiency.native_or_bilingual: "Native or bilingual proficiency",
}


def header_links(profile: Profile) -> list[str]:
    """LinkedIn, GitHub, Portfolio as plain URLs: the profile fields first, then the
    matching entries of the links list when a field is empty."""
    by_kind: dict[LinkKind, str] = {}
    for link in profile.links:
        by_kind.setdefault(link.kind, link.url)
    urls = [
        profile.linkedin_url or by_kind.get(LinkKind.linkedin),
        profile.github_url or by_kind.get(LinkKind.github),
        profile.portfolio_url or by_kind.get(LinkKind.portfolio) or by_kind.get(LinkKind.website),
    ]
    return list(dict.fromkeys(url for url in urls if url))


def work_authorization_line(profile: Profile) -> str | None:
    """One short line, only from what the user set. None when nothing is set."""
    country = country_name(profile.work_authorization_country)
    parts: list[str] = []
    if profile.work_authorization == WorkAuthorization.authorized:
        parts.append(f"Authorized to work in {country}" if country else "Authorized to work")
    elif profile.work_authorization == WorkAuthorization.requires_sponsorship:
        parts.append(f"Requires visa sponsorship for {country}" if country else "Requires visa sponsorship")
    if profile.open_to_relocation:
        parts.append(f"Open to relocation to {country}" if country and not parts else "Open to relocation")
    return " | ".join(parts) or None


def language_lines(profile: Profile) -> list[str]:
    lines: list[str] = []
    english_level = EnglishLevel(profile.english_level) if profile.english_level else None
    has_english = False
    for lang in profile.languages:
        code = lang.language_code.lower()
        name = LANGUAGE_NAMES.get(code, code.upper())
        label = _PROFICIENCY_LABELS[LanguageProficiency(lang.proficiency)]
        if code == "en" and english_level:
            has_english = True
            label = english_level.value if english_level is EnglishLevel.native else f"{english_level.value} ({label})"
        lines.append(f"{name} - {label}")
    if english_level and not has_english:
        lines.append(f"English - {english_level.value}")
    return lines


def _education_dates(edu: Education) -> str:
    if edu.start_date or edu.end_date:
        return format_range(edu.start_date, edu.end_date)
    return format_year_range(edu.start_year, edu.end_year)


def build_ats_document(profile: Profile, offer: str | None = None) -> ATSDocument:
    full_name = " ".join(part for part in (profile.first_name, profile.last_name) if part)
    location = ", ".join(x for x in (profile.city, profile.region, country_name(profile.country_code)) if x)
    contact = " | ".join(x for x in (location, profile.phone, profile.contact_email) if x)
    selected = select_skills(profile.skills, offer, profile.experiences)

    return ATSDocument(
        full_name=full_name or "Curriculum Vitae",
        headline=profile.headline or None,
        contact_line=contact or None,
        links=header_links(profile),
        work_authorization_line=work_authorization_line(profile),
        summary=profile.summary or None,
        skill_lines=skill_lines(selected),
        experiences=[
            ATSExperience(
                experience_id=exp.id,
                position=exp.position,
                employer=exp.employer.name,
                client=exp.client.name if exp.client else None,
                start=exp.start_date,
                end=exp.end_date,
                current=exp.end_date is None,
                area=exp.area,
                description=exp.description or None,
                bullets=[function.description for function in exp.functions if function.description.strip()],
            )
            for exp in sorted(profile.experiences, key=lambda e: e.start_date, reverse=True)
            if exp.is_active
        ],
        educations=[
            ATSEducation(
                title=f"{edu.degree}{f', {edu.field_of_study}' if edu.field_of_study else ''} - {edu.institution}",
                institution=edu.institution,
                dates=_education_dates(edu),
                description=edu.description or None,
            )
            for edu in profile.educations
            if edu.is_active
        ],
        certifications=[
            ATSCertification(f"{cert.name} - {cert.issuing_organization}", format_range(cert.issue_date, cert.expiration_date))
            for cert in profile.certifications
            if cert.is_active
        ],
        projects=[
            ATSProject(project.name, project.description or None) for project in profile.projects if project.is_active
        ],
        languages=language_lines(profile),
    )
