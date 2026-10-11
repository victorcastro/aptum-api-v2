"""Profile -> ATSDocument. Every value comes from the profile; nothing is generated here."""

from aptum.common.countries import country_name
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
from aptum.modules.cv.header import availability_line
from aptum.modules.cv.links import header_links
from aptum.modules.profile.models import Education, Profile


def language_lines(profile: Profile) -> list[str]:
    """`Spanish - Native`, `English - C1`: language name and level code from the catalogs."""
    return [f"{lang.language.name} - {lang.proficiency}" for lang in profile.languages if lang.is_active]


def education_dates(edu: Education) -> str:
    return format_year_range(edu.start_year, edu.end_year)


def education_location(edu: Education) -> str:
    """`Lima, Peru`: the city and the country name, whichever are set."""
    return ", ".join(part for part in (edu.location_city, country_name(edu.location_country_code)) if part)


def _ats_education(edu: Education) -> ATSEducation:
    location = education_location(edu)
    place = ", ".join(part for part in (edu.institution, location) if part)
    field = f", {edu.field_of_study}" if edu.field_of_study else ""
    return ATSEducation(
        title=f"{edu.degree.name}{field} - {place}",
        institution=edu.institution,
        dates=education_dates(edu),
        location=location,
    )


def build_ats_document(profile: Profile, offer: str | None = None) -> ATSDocument:
    full_name = " ".join(part for part in (profile.first_name, profile.last_name) if part)
    selected = select_skills(profile.skills, offer, profile.experiences)

    return ATSDocument(
        full_name=full_name or "Curriculum Vitae",
        headline=profile.headline or None,
        availability_line=availability_line(profile),
        phone=profile.phone or None,
        email=profile.contact_email or None,
        links=header_links(profile),
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
                skills_line=", ".join(s.name for s in exp.skills) or None,
            )
            for exp in sorted(profile.experiences, key=lambda e: e.start_date, reverse=True)
            if exp.is_active
        ],
        educations=[
            _ats_education(edu)
            for edu in profile.educations
            if edu.is_active
        ],
        certifications=[
            ATSCertification(
                cert.name,
                cert.issuing_organization,
                format_range(cert.issue_date, cert.expiration_date),
                cert.credential_url if cert.show_credential_url else None,
            )
            for cert in profile.certifications
            if cert.is_active
        ],
        projects=[
            ATSProject(project.name, project.description or None, project.url if project.show_url else None)
            for project in profile.projects
            if project.is_active
        ],
        languages=language_lines(profile),
    )
