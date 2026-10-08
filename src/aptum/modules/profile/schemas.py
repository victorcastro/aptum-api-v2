from typing import Annotated, ClassVar
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    model_validator,
)

from aptum.common.enums import (
    EmploymentType,
    ExperienceArea,
    LinkKind,
    SkillCategory,
    SkillLevel,
    WorkAuthorization,
    WorkMode,
)
from aptum.common.types import CountryCode, LanguageCode, YearMonth
from aptum.modules.companies.schemas import CompanySummary
from aptum.modules.skills.schemas import SkillRead


def _check_range(start, end) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_date must not be before start_date")


_HTTP_URL = TypeAdapter(HttpUrl)


def _check_http_url(value: str) -> str:
    _HTTP_URL.validate_python(value)
    return value


HttpUrlStr = Annotated[str, Field(max_length=500), AfterValidator(_check_http_url)]


def _host_check(*domains: str):
    def check(value: str) -> str:
        host = (urlsplit(value).hostname or "").lower()
        if not any(host == domain or host.endswith("." + domain) for domain in domains):
            raise ValueError(f"Expected a {' or '.join(domains)} URL")
        return value

    return AfterValidator(check)


_KIND_HOSTS = {LinkKind.linkedin: ("linkedin.com",), LinkKind.github: ("github.com",)}
MAX_LINKS = 10
Year = Annotated[int, Field(ge=1900, le=2100)]


def _check_years(start: int | None, end: int | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_year must not be before start_year")


def _check_dates(issue, expiration) -> None:
    if issue is not None and expiration is not None and expiration < issue:
        raise ValueError("expiration_date must not be before issue_date")


class ProfileLink(BaseModel):
    """One header link of the CV. `visible` only controls the CV: the URL stays on the profile."""

    kind: LinkKind
    label: Annotated[str, Field(max_length=120)] | None = None
    url: HttpUrlStr
    visible: bool = True

    @model_validator(mode="after")
    def _check_host(self):
        if self.kind in _KIND_HOSTS:
            _host_check(*_KIND_HOSTS[self.kind]).func(self.url)
        return self


def _check_links(links: list[ProfileLink]) -> list[ProfileLink]:
    kinds = [link.kind for link in links if link.kind != LinkKind.other]
    if len(kinds) != len(set(kinds)):
        raise ValueError("Only one link per kind (use 'other' for extra ones)")
    return links


ProfileLinks = Annotated[
    list[ProfileLink], Field(max_length=MAX_LINKS), AfterValidator(_check_links)
]


class ExperienceCreate(BaseModel):
    position: str
    employer_id: int
    client_id: int | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    location_city: str | None = None
    location_country_code: CountryCode | None = None
    start_date: YearMonth
    end_date: YearMonth | None = None
    is_active: bool = True
    description: str | None = None
    functions: list[str] = Field(default_factory=list)
    skill_ids: list[int] = Field(default_factory=list, description="Catalog skills used in this role.")
    area: ExperienceArea | None = Field(default=None, description="Used for per-area years of experience.")

    @model_validator(mode="after")
    def _validate(self):
        _check_range(self.start_date, self.end_date)
        if self.client_id is not None and self.client_id == self.employer_id:
            raise ValueError("client_id must differ from employer_id")
        return self


class ExperienceFunctionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: str
    employer: CompanySummary
    client: CompanySummary | None
    employment_type: EmploymentType | None
    work_mode: WorkMode | None
    location_city: str | None
    location_country_code: str | None
    start_date: YearMonth
    end_date: YearMonth | None
    is_current: bool
    is_active: bool
    description: str | None
    area: ExperienceArea | None = None
    functions: list[ExperienceFunctionRead] = []
    skills: list[SkillRead] = []


class PartialUpdate(BaseModel):
    """Base for PATCH bodies: only the fields sent change, and `non_nullable` ones reject null."""

    non_nullable: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _reject_null(self):
        for field in self.non_nullable:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ExperienceUpdate(PartialUpdate):
    non_nullable = ("position", "employer_id", "start_date", "is_active", "functions", "skill_ids")

    position: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    employer_id: int | None = None
    client_id: int | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    location_city: str | None = None
    location_country_code: CountryCode | None = None
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    is_active: bool | None = None
    description: str | None = None
    functions: list[str] | None = None
    skill_ids: list[int] | None = None
    area: ExperienceArea | None = None


class EducationCreate(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    start_year: Year | None = Field(default=None, description="Year-only start, when the month is unknown.")
    end_year: Year | None = Field(default=None, description="Year-only end (or expected graduation year).")
    grade: str | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _validate(self):
        _check_range(self.start_date, self.end_date)
        _check_years(self.start_year, self.end_year)
        return self


class EducationUpdate(PartialUpdate):
    non_nullable = ("institution", "degree", "is_active")

    institution: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    degree: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    field_of_study: str | None = None
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    start_year: Year | None = None
    end_year: Year | None = None
    grade: str | None = None
    is_active: bool | None = None


class EducationRead(EducationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


LanguageLevelCode = Annotated[
    str,
    Field(min_length=1, max_length=8, description="Code from `GET /commons/language-levels` (A1-C2, Native)."),
]


class LanguageCreate(BaseModel):
    language_code: LanguageCode = Field(description="Code from `GET /commons/languages` (ISO 639-1).")
    proficiency: LanguageLevelCode
    is_active: bool = True


class LanguageUpdate(PartialUpdate):
    non_nullable = ("proficiency", "is_active")

    proficiency: LanguageLevelCode | None = None
    is_active: bool | None = None


class LanguageRead(LanguageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class ProfileSkillCreate(BaseModel):
    skill_id: int
    level: SkillLevel | None = None
    years_experience: Annotated[int, Field(ge=0, le=80)] | None = None
    category: SkillCategory | None = Field(
        default=None, description="CV group. Omitted or null: classified from the skill dictionary."
    )


class ProfileSkillUpdate(PartialUpdate):
    level: SkillLevel | None = None
    years_experience: Annotated[int, Field(ge=0, le=80)] | None = None
    category: SkillCategory | None = Field(
        default=None, description="CV group. `null` re-classifies it from the skill dictionary."
    )


class ProfileSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill: SkillRead
    level: SkillLevel | None
    years_experience: int | None
    category: SkillCategory


class ProfileSkillItem(BaseModel):
    """`id` is the profile skill (PATCH/DELETE); `skill_id` is the shared catalog skill."""

    id: int
    skill_id: int
    name: str
    level: SkillLevel | None
    years_experience: int | None


class ProfileSkillGroup(BaseModel):
    category: SkillCategory
    skills: list[ProfileSkillItem]


class ProfileSkillsGrouped(BaseModel):
    total: int
    groups: list[ProfileSkillGroup]


class CertificationCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    issuing_organization: Annotated[str, Field(min_length=1, max_length=255)]
    issue_date: YearMonth | None = None
    expiration_date: YearMonth | None = None
    credential_id: Annotated[str, Field(max_length=255)] | None = None
    credential_url: HttpUrlStr | None = None
    show_credential_url: bool = True
    is_active: bool = True

    @model_validator(mode="after")
    def _validate(self):
        _check_dates(self.issue_date, self.expiration_date)
        return self


class CertificationUpdate(PartialUpdate):
    non_nullable = ("name", "issuing_organization", "is_active")

    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    issuing_organization: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    issue_date: YearMonth | None = None
    expiration_date: YearMonth | None = None
    credential_id: Annotated[str, Field(max_length=255)] | None = None
    credential_url: HttpUrlStr | None = None
    show_credential_url: bool | None = None
    is_active: bool | None = None


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    issuing_organization: str
    issue_date: YearMonth | None
    expiration_date: YearMonth | None
    credential_id: str | None
    credential_url: str | None
    show_credential_url: bool
    is_active: bool


class ProjectCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    url: HttpUrlStr | None = None
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    show_url: bool = True
    is_active: bool = True

    @model_validator(mode="after")
    def _validate(self):
        _check_range(self.start_date, self.end_date)
        return self


class ProjectUpdate(PartialUpdate):
    non_nullable = ("name", "show_url", "is_active")

    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    url: HttpUrlStr | None = None
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    show_url: bool | None = None
    is_active: bool | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    url: str | None
    start_date: YearMonth | None
    end_date: YearMonth | None
    show_url: bool
    is_active: bool


class ProfileUpdate(PartialUpdate):
    non_nullable = ("open_to_relocation", "links")

    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    phone: str | None = None
    contact_email: str | None = None
    city: str | None = None
    country_code: CountryCode | None = None
    links: ProfileLinks | None = None
    work_authorization: WorkAuthorization | None = None
    work_authorization_country: CountryCode | None = Field(
        default=None, description="Country the authorization or relocation refers to."
    )
    open_to_relocation: bool | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    first_name: str | None
    last_name: str | None
    headline: str | None
    summary: str | None
    phone: str | None
    contact_email: str | None
    city: str | None
    country_code: str | None
    links: list[ProfileLink] = []
    work_authorization: WorkAuthorization | None = None
    work_authorization_country: str | None = None
    open_to_relocation: bool = False
    experiences: list[ExperienceRead] = []
    educations: list[EducationRead] = []
    languages: list[LanguageRead] = []
    skills: list[ProfileSkillRead] = []
    certifications: list[CertificationRead] = []
    projects: list[ProjectRead] = []
