from pydantic import BaseModel


class CVTemplateOut(BaseModel):
    id: str
    name: str
    description: str
    selected: bool


class CVTemplateChoice(BaseModel):
    """`template_id: null` clears the saved preference, so exports go back to the default."""

    template_id: str | None = None
