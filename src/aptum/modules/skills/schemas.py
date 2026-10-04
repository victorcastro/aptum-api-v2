from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    category: str | None


class SkillCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    category: Annotated[str, Field(max_length=80)] | None = None


class SkillUpdate(BaseModel):
    """Moderation of the shared catalog. Partial: only the fields sent change; `category` may be
    null. Does not touch the CV group (`profile_skills.category`) of profiles that use the skill."""

    name: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    category: Annotated[str, Field(max_length=80)] | None = None
