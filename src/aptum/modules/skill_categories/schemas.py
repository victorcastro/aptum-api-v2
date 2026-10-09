from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

CategoryName = Annotated[str, Field(min_length=1, max_length=40)]


class SkillCategoryRef(BaseModel):
    """What a profile skill shows of its category."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SkillCategoryRead(SkillCategoryRef):
    position: int


class SkillCategoryCreate(BaseModel):
    name: CategoryName


class SkillCategoryUpdate(BaseModel):
    name: CategoryName


class SkillCategoryOrder(BaseModel):
    ids: Annotated[list[int], Field(min_length=1, description="Every category id of the caller, in the new order.")]
