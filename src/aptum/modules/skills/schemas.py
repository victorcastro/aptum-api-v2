from pydantic import BaseModel, ConfigDict


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    category: str | None
