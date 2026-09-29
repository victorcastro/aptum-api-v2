from pydantic import BaseModel, ConfigDict, Field, model_validator

from aptum.common.enums import (
    EmploymentType,
    LanguageProficiency,
    LinkKind,
    SkillLevel,
    WorkMode,
)
from aptum.common.types import CountryCode, LanguageCode, YearMonth
from aptum.modules.companies.schemas import CompanyRead
from aptum.modules.skills.schemas import SkillRead


def _check_range(start, end) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_date must not be before start_date")


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
    description: str | None = None
    functions: list[str] = Field(default_factory=list)

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
    position: int


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: str
    employer: CompanyRead
    client: CompanyRead | None
    employment_type: EmploymentType | None
    work_mode: WorkMode | None
    location_city: str | None
    location_country_code: str | None
    start_date: YearMonth
    end_date: YearMonth | None
    is_current: bool
    description: str | None
    functions: list[ExperienceFunctionRead] = []


class EducationCreate(BaseModel):
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: YearMonth | None = None
    end_date: YearMonth | None = None
    grade: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _validate(self):
        _check_range(self.start_date, self.end_date)
        return self


class EducationRead(EducationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LanguageCreate(BaseModel):
    language_code: LanguageCode
    proficiency: LanguageProficiency


class LanguageRead(LanguageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProfileLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: LinkKind
    url: str
    label: str | None


class ProfileSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill: SkillRead
    level: SkillLevel | None
    years_experience: int | None


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    issuing_organization: str
    issue_date: YearMonth | None
    expiration_date: YearMonth | None
    credential_id: str | None
    credential_url: str | None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    url: str | None
    start_date: YearMonth | None
    end_date: YearMonth | None


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    phone: str | None = None
    contact_email: str | None = None
    city: str | None = None
    region: str | None = None
    country_code: CountryCode | None = None


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
    region: str | None
    country_code: str | None
    links: list[ProfileLinkRead] = []
    experiences: list[ExperienceRead] = []
    educations: list[EducationRead] = []
    languages: list[LanguageRead] = []
    skills: list[ProfileSkillRead] = []
    certifications: list[CertificationRead] = []
    projects: list[ProjectRead] = []
