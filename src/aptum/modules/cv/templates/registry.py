from dataclasses import dataclass

from aptum.core.exceptions import NotFoundError
from aptum.modules.cv.templates.base import CVTemplate
from aptum.modules.cv.templates.classic import ClassicTemplate
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate

DEFAULT_TEMPLATE = "classic"


@dataclass(frozen=True)
class TemplateInfo:
    id: str
    name: str
    description: str


_TEMPLATES: dict[str, tuple[TemplateInfo, CVTemplate]] = {
    "classic": (
        TemplateInfo("classic", "Classic", "Single column with standard headings."),
        ClassicTemplate(),
    ),
    "software-engineer": (
        TemplateInfo(
            "software-engineer",
            "Software Engineer",
            "Plain black-on-white layout for ATS, technical skills grouped by category before experience.",
        ),
        SoftwareEngineerTemplate(),
    ),
}


def list_templates() -> list[TemplateInfo]:
    return [info for info, _ in _TEMPLATES.values()]


def has_template(template_id: str) -> bool:
    return template_id in _TEMPLATES


def get_template(template_id: str) -> CVTemplate:
    entry = _TEMPLATES.get(template_id)
    if entry is None:
        raise NotFoundError(f"Template '{template_id}' not found")
    return entry[1]
