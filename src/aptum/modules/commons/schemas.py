from pydantic import BaseModel, ConfigDict


class CountryRead(BaseModel):
    code: str
    name: str


class LanguageOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class LanguageLevelOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
