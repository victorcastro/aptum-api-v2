from pydantic import BaseModel, ConfigDict


class ExperienceCreate(BaseModel):
    company: str
    role: str
    description: str | None = None


class ExperienceRead(ExperienceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EducationCreate(BaseModel):
    institution: str
    degree: str


class EducationRead(EducationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class LanguageCreate(BaseModel):
    name: str
    level: str


class LanguageRead(LanguageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProfileUpdate(BaseModel):
    headline: str | None = None
    summary: str | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    headline: str | None
    summary: str | None
    experiences: list[ExperienceRead] = []
    educations: list[EducationRead] = []
    languages: list[LanguageRead] = []
