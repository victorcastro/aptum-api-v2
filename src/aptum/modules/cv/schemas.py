from pydantic import BaseModel


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
