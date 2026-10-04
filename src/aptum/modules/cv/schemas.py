from typing import Annotated

from pydantic import BaseModel, Field


class CVTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    selected: bool


class CVSettingsRead(BaseModel):
    """`template_id` is the template `/cv/export` uses by default: the saved one, or `basic`."""

    template_id: str


class CVSettingsUpdate(BaseModel):
    """Partial update: omitted fields keep their value, `null` clears the field back to its default."""

    template_id: str | None = None


class ATSGenerateRequest(BaseModel):
    """`job_description` is optional: with it, skills are selected and ordered for the offer."""

    job_description: Annotated[str, Field(max_length=30_000)] | None = None


class CVWarningOut(BaseModel):
    code: str = Field(examples=["missing_metric"])
    message: str
    section: str | None = None
    item: str | None = Field(default=None, description="Role, institution or entry the warning is about.")
    text: str | None = Field(default=None, description="The exact text concerned.")
    suggestion: str | None = None


class FidelityIssueOut(BaseModel):
    kind: str = Field(description="employer | title | date | number")
    value: str
    location: str
    message: str


class KeywordCoverageOut(BaseModel):
    offer_keywords: list[str]
    present_in_cv: list[str]
    missing: list[str]
    supported_by_profile: list[str] = Field(
        description="Missing keywords that the profile does contain (suggested, never added)."
    )
    coverage: float = Field(description="present_in_cv / offer_keywords, 0..1.")
    suggestions: list[str]


class YearsOfExperienceOut(BaseModel):
    total: int
    by_area: dict[str, int]


class SkillLineOut(BaseModel):
    category: str
    names: list[str]


class ATSReport(BaseModel):
    """Everything the ATS pipeline knows about the CV it generated. None of it is in the PDF."""

    page_count: int
    years_of_experience: YearsOfExperienceOut
    skills: list[SkillLineOut]
    warnings: list[CVWarningOut]
    fidelity_issues: list[FidelityIssueOut]
    keyword_coverage: KeywordCoverageOut | None
