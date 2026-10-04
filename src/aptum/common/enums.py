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


class WorkAuthorization(StrEnum):
    authorized = "authorized"
    requires_sponsorship = "requires_sponsorship"


class UserRole(StrEnum):
    """One role per user. What each role may do lives only in core/permissions.py."""

    user = "user"
    moderator = "moderator"
    admin = "admin"


class ExperienceArea(StrEnum):
    """Used to compute per-area years of experience."""

    backend = "backend"
    mobile = "mobile"
    ai = "ai"
    other = "other"


class AuditEntity(StrEnum):
    company = "company"
    skill = "skill"
    industry = "industry"
    user = "user"


class AuditAction(StrEnum):
    company_update = "company.update"
    company_merge = "company.merge"
    company_delete = "company.delete"
    skill_update = "skill.update"
    industry_create = "industry.create"
    industry_update = "industry.update"
    user_role_change = "user.role_change"
    user_activate = "user.activate"
    user_deactivate = "user.deactivate"
