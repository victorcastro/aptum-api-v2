from enum import StrEnum


class WorkMode(StrEnum):
    remote = "remote"
    onsite = "onsite"
    hybrid = "hybrid"


class EmploymentType(StrEnum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    freelance = "freelance"
    self_employed = "self_employed"
    internship = "internship"
    apprenticeship = "apprenticeship"
    temporary = "temporary"


class LanguageProficiency(StrEnum):
    elementary = "elementary"
    limited_working = "limited_working"
    professional_working = "professional_working"
    full_professional = "full_professional"
    native_or_bilingual = "native_or_bilingual"


class SkillLevel(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class LinkKind(StrEnum):
    linkedin = "linkedin"
    github = "github"
    portfolio = "portfolio"
    website = "website"
    other = "other"


class SkillCategory(StrEnum):
    """CV skill groups, in the order the CV prints them. Values are what gets stored and printed."""

    llms_ai = "LLMs & AI"
    backend = "Backend"
    cloud_devops = "Cloud & DevOps"
    architecture = "Architecture"
    mobile = "Mobile"
    other = "Other"
