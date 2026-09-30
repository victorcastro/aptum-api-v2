from dataclasses import dataclass
from datetime import date

from aptum.common.enums import LinkKind
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
    dates: str
    description: str | None


@dataclass(frozen=True)
class CertificationEntry:
    title: str
    dates: str


@dataclass(frozen=True)
class ProjectEntry:
    name: str
    description: str | None


@dataclass(frozen=True)
class SkillGroup:
    label: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class LinkEntry:
    label: str
    url: str


@dataclass(frozen=True)
class CVDocument:
    """Presentation-ready CV: every value is already formatted, templates only lay it out."""

    full_name: str
    headline: str | None
    contact_line: str | None
    links_line: str | None
    location: str | None
    phone: str | None
    email: str | None
    links: tuple[LinkEntry, ...]
    summary: str | None
    experiences: tuple[ExperienceEntry, ...]
    educations: tuple[EducationEntry, ...]
    skills_line: str | None
    skill_groups: tuple[SkillGroup, ...]
    languages_line: str | None
    certifications: tuple[CertificationEntry, ...]
    projects: tuple[ProjectEntry, ...]


_LINK_LABELS = {
    LinkKind.linkedin: "LinkedIn",
    LinkKind.github: "GitHub",
    LinkKind.portfolio: "Portfolio",
    LinkKind.website: "Website",
}


def _month(value: date | None) -> str:
    return value.strftime("%b %Y") if value else ""


def _range(start: date | None, end: date | None, current: bool = False) -> str:
    if start is None and end is None:
        return ""
    return f"{_month(start)} - {'Present' if current else _month(end)}".strip(" -")


def _group_skills(profile: Profile) -> tuple[SkillGroup, ...]:
    """Group by Skill.category in order of first appearance; uncategorized skills go to "Other"."""
    groups: dict[str, list[str]] = {}
    for ps in profile.skills:
        groups.setdefault(ps.skill.category or "Other", []).append(ps.skill.name)
    return tuple(SkillGroup(label, tuple(names)) for label, names in groups.items())


def build_cv_data(profile: Profile) -> CVDocument:
    full_name = " ".join(part for part in (profile.first_name, profile.last_name) if part)
    location = ", ".join(x for x in (profile.city, profile.region, profile.country_code) if x)
    links = tuple(
        LinkEntry(_LINK_LABELS.get(link.kind) or link.label or "Link", link.url)
        for link in sorted(profile.links, key=lambda link: link.kind != LinkKind.linkedin)
    )
    contact = " | ".join(x for x in (profile.contact_email, profile.phone, location) if x)

    experiences = tuple(
        ExperienceEntry(
            title=f"{exp.position} - {exp.employer.name}"
            + (f" (client: {exp.client.name})" if exp.client else ""),
            dates=_range(exp.start_date, exp.end_date, exp.is_current),
            description=exp.description or None,
            bullets=tuple(function.description for function in exp.functions),
            skills_line=", ".join(s.name for s in exp.skills) if exp.skills else None,
        )
        for exp in profile.experiences
    )
    educations = tuple(
        EducationEntry(
            title=f"{edu.degree}{f', {edu.field_of_study}' if edu.field_of_study else ''} - {edu.institution}",
            dates=_range(edu.start_date, edu.end_date),
            description=edu.description or None,
        )
        for edu in profile.educations
    )
    certifications = tuple(
        CertificationEntry(
            title=f"{cert.name} - {cert.issuing_organization}",
            dates=_range(cert.issue_date, cert.expiration_date),
        )
        for cert in profile.certifications
    )
    projects = tuple(
        ProjectEntry(name=project.name, description=project.description or None)
        for project in profile.projects
    )

    return CVDocument(
        full_name=full_name or "Curriculum Vitae",
        headline=profile.headline or None,
        contact_line=contact or None,
        links_line=" | ".join(link.url for link in profile.links) if profile.links else None,
        location=", ".join(x for x in (profile.city, profile.country_code) if x) or None,
        phone=profile.phone or None,
        email=profile.contact_email or None,
        links=links,
        summary=profile.summary or None,
        experiences=experiences,
        educations=educations,
        skills_line=", ".join(ps.skill.name for ps in profile.skills) if profile.skills else None,
        skill_groups=_group_skills(profile),
        languages_line=", ".join(
            f"{lang.language_code.upper()} ({lang.proficiency.value.replace('_', ' ')})"
            for lang in profile.languages
        )
        if profile.languages
        else None,
        certifications=certifications,
        projects=projects,
    )
