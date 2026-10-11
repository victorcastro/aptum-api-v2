from pydantic import BaseModel, ConfigDict


class CountryRead(BaseModel):
    code: str
    name: str


class DegreeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class DegreeGroupRead(BaseModel):
    heading: str
    options: list[DegreeRead]


class LanguageOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class LanguageLevelOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
