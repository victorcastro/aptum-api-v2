from pydantic import BaseModel, ConfigDict

from aptum.common.types import CountryCode


class IndustryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class CompanyCreate(BaseModel):
    name: str
    industry_id: int | None = None
    city: str | None = None
    country_code: CountryCode | None = None
    website: str | None = None
    is_consultancy: bool = False


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: IndustryRead | None
    city: str | None
    country_code: str | None
    website: str | None
    logo_url: str | None
    is_consultancy: bool
