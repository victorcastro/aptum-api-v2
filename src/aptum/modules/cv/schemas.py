from typing import Annotated

from pydantic import BaseModel, Field


class CVTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    selected: bool


class CVSettingsRead(BaseModel):
    """`template_id` is the template `/cv/export` uses by default: the saved one, or `classic`."""

    template_id: str


class CVSettingsUpdate(BaseModel):
    """Partial update: omitted fields keep their value, `null` clears the field back to its default."""

    template_id: str | None = None


class ATSGenerateRequest(BaseModel):
    """`job_description` is optional: with it, skills are selected and ordered for the offer."""

    job_description: Annotated[str, Field(max_length=30_000)] | None = None
