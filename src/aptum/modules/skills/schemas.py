from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class SkillCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]


class SkillUpdate(BaseModel):
    """Rename a shared catalog skill. The CV group lives on each profile (`profile_skills.category`)."""

    name: Annotated[str, Field(min_length=1, max_length=120)]
