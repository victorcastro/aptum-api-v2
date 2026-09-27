from pydantic import BaseModel, ConfigDict


class CVRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    raw_text: str | None
