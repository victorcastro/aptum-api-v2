"""ATS CV document: structured (not pre-formatted) so the generation rules and the fidelity
check can work on employers, titles and dates, and the template only lays it out."""

from dataclasses import dataclass, field
from datetime import date

from aptum.modules.cv.ats.skills import SkillLine

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def format_month(value: date) -> str:
    """'Mon YYYY' in English regardless of the server locale."""
    return f"{_MONTHS[value.month - 1]} {value.year}"


def format_range(start: date | None, end: date | None, current: bool = False) -> str:
    """'Mon YYYY - Mon YYYY', 'Mon YYYY - Present', or just one side when the other is unknown."""
    left = format_month(start) if start else ""
    right = "Present" if current else (format_month(end) if end else "")
    return " - ".join(part for part in (left, right) if part)


def format_year_range(start: int | None, end: int | None) -> str:
    return " - ".join(str(year) for year in (start, end) if year)


@dataclass
class ATSExperience:
    experience_id: int | None
    position: str
    employer: str
    client: str | None
    start: date
    end: date | None
    current: bool
    area: str | None
    description: str | None
    bullets: list[str]
    compressed: bool = False

    @property
    def company_line(self) -> str:
        return f"{self.client} (via {self.employer})" if self.client else self.employer

    @property
    def title(self) -> str:
        return f"{self.position} - {self.company_line}"

    @property
    def dates(self) -> str:
        return format_range(self.start, self.end, self.current)


@dataclass
class ATSEducation:
    title: str
    institution: str
    dates: str
    description: str | None


@dataclass
class ATSCertification:
    title: str
    dates: str


@dataclass
class ATSProject:
    name: str
    description: str | None


@dataclass
class ATSDocument:
    full_name: str
    headline: str | None
    contact_line: str | None
    links: list[str]
    work_authorization_line: str | None
    summary: str | None
    skill_lines: list[SkillLine]
    experiences: list[ATSExperience]
    educations: list[ATSEducation]
    certifications: list[ATSCertification]
    projects: list[ATSProject]
    languages: list[str]
    selected_skills: list[str] = field(default_factory=list)

    def text_blocks(self) -> list[tuple[str, str]]:
        """Every piece of free text as (location, text), for checks that scan the whole CV."""
        blocks: list[tuple[str, str]] = []
        if self.headline:
            blocks.append(("headline", self.headline))
        if self.summary:
            blocks.append(("summary", self.summary))
        for line in self.skill_lines:
            blocks.append(("skills", line.render()))
        for exp in self.experiences:
            blocks.append((f"experience:{exp.title}", exp.title))
            if exp.description:
                blocks.append((f"experience:{exp.title}", exp.description))
            blocks.extend((f"experience:{exp.title}", bullet) for bullet in exp.bullets)
        for edu in self.educations:
            blocks.append(("education", edu.title))
            if edu.description:
                blocks.append(("education", edu.description))
        blocks.extend(("certifications", cert.title) for cert in self.certifications)
        for project in self.projects:
            blocks.append(("projects", project.name))
            if project.description:
                blocks.append(("projects", project.description))
        blocks.extend(("languages", language) for language in self.languages)
        return blocks

    def plain_text(self) -> str:
        return "\n".join(text for _, text in self.text_blocks())
