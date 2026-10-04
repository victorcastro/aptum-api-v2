from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from aptum.common.types import CountryCode


class IndustryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class IndustryWrite(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]


class CompanyMerge(BaseModel):
    """The company that survives; the one in the path is deleted."""

    target_id: int


class CompanyCreate(BaseModel):
    name: str
    industry_id: int | None = None
    city: str | None = None
    country_code: CountryCode | None = None
    website: str | None = None
    is_consultancy: bool = False


class CompanyUpdate(BaseModel):
    """Partial update: only the fields sent are changed."""

    name: str | None = None
    industry_id: int | None = None
    city: str | None = None
    country_code: CountryCode | None = None
    website: str | None = None
    is_consultancy: bool | None = None


class CompanySummary(BaseModel):
    """A company as embedded in other resources (experiences)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: IndustryRead | None
    city: str | None
    country_code: str | None
    website: str | None
    logo_url: str | None
    is_consultancy: bool


class CompanyRead(CompanySummary):
    """A company from /companies, with what the caller may do with it."""

    # Whether the caller may PATCH this company. UI hint only: every write is checked again.
    can_edit: bool = False
