from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


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


class DegreeDetailRead(DegreeRead):
    level: str
    rank: int


class DegreeCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    level: Annotated[str, Field(min_length=1, max_length=40)]


class DegreeUpdate(BaseModel):
    """Only the fields sent change. A new `level` moves the degree to the end of that level."""

    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    level: Annotated[str, Field(min_length=1, max_length=40)] | None = None


class LanguageOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class LanguageLevelOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
