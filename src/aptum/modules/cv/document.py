from dataclasses import dataclass

from aptum.common.enums import SkillCategory
from aptum.modules.cv.ats.builder import education_dates, language_lines
from aptum.modules.cv.ats.document import format_range
from aptum.modules.cv.header import availability_line
from aptum.modules.cv.links import LinkEntry, header_links
from aptum.modules.profile.models import Profile


@dataclass(frozen=True)
class ExperienceEntry:
    title: str
    dates: str
    description: str | None
    bullets: tuple[str, ...]
    skills_line: str | None


@dataclass(frozen=True)
class EducationEntry:
    title: str
    institution: str
    dates: str


@dataclass(frozen=True)
class CertificationEntry:
    title: str
    issuer: str
    dates: str
    url: str | None = None


@dataclass(frozen=True)
class ProjectEntry:
    name: str
    description: str | None
    url: str | None = None


@dataclass(frozen=True)
class SkillGroup:
    label: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class CVDocument:
    """Presentation-ready CV: every value is already formatted, templates only lay it out."""

    full_name: str
    headline: str | None
    availability_line: str | None
    phone: str | None
    email: str | None
    links: tuple[LinkEntry, ...]
    summary: str | None
    experiences: tuple[ExperienceEntry, ...]
    educations: tuple[EducationEntry, ...]
    skills_line: str | None
    skill_groups: tuple[SkillGroup, ...]
    languages: tuple[str, ...]
    certifications: tuple[CertificationEntry, ...]
    projects: tuple[ProjectEntry, ...]


def _group_skills(profile: Profile) -> tuple[SkillGroup, ...]:
    """Group by the profile skill's CV category, in `SkillCategory` order like the ATS CV;
    empty groups are left out."""
    groups: dict[str, list[str]] = {}
    for ps in profile.skills:
        groups.setdefault(ps.category, []).append(ps.skill.name)
    return tuple(
        SkillGroup(category.value, tuple(groups[category.value]))
        for category in SkillCategory
        if category.value in groups
    )


def build_cv_data(profile: Profile) -> CVDocument:
    full_name = " ".join(part for part in (profile.first_name, profile.last_name) if part)

    experiences = tuple(
        ExperienceEntry(
            title=f"{exp.position} - "
            + (f"{exp.client.name} (via {exp.employer.name})" if exp.client else exp.employer.name),
            dates=format_range(exp.start_date, exp.end_date, exp.is_current),
            description=exp.description or None,
            bullets=tuple(function.description for function in exp.functions if function.description.strip()),
            skills_line=", ".join(s.name for s in exp.skills) if exp.skills else None,
        )
        for exp in profile.experiences
        if exp.is_active
    )
    educations = tuple(
        EducationEntry(
            title=f"{edu.degree}{f', {edu.field_of_study}' if edu.field_of_study else ''}",
            institution=edu.institution,
            dates=education_dates(edu),
        )
        for edu in profile.educations
        if edu.is_active
    )
    certifications = tuple(
        CertificationEntry(
            title=cert.name,
            issuer=cert.issuing_organization,
            dates=format_range(cert.issue_date, cert.expiration_date),
            url=(cert.credential_url if cert.show_credential_url else None),
        )
        for cert in profile.certifications
        if cert.is_active
    )
    projects = tuple(
        ProjectEntry(
            name=project.name,
            description=project.description or None,
            url=(project.url if project.show_url else None),
        )
        for project in profile.projects
        if project.is_active
    )

    return CVDocument(
        full_name=full_name or "Curriculum Vitae",
        headline=profile.headline or None,
        availability_line=availability_line(profile),
        phone=profile.phone or None,
        email=profile.contact_email or None,
        links=tuple(header_links(profile)),
        summary=profile.summary or None,
        experiences=experiences,
        educations=educations,
        skills_line=", ".join(ps.skill.name for ps in profile.skills) if profile.skills else None,
        skill_groups=_group_skills(profile),
        languages=tuple(language_lines(profile)),
        certifications=certifications,
        projects=projects,
    )
