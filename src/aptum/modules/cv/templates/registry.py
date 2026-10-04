from dataclasses import dataclass

from aptum.core.exceptions import NotFoundError
from aptum.modules.cv.templates.base import CVTemplate
from aptum.modules.cv.templates.software_engineer import SoftwareEngineerTemplate

BASIC_TEMPLATE = "basic"
DEFAULT_TEMPLATE = BASIC_TEMPLATE


@dataclass(frozen=True)
class TemplateInfo:
    id: str
    name: str
    description: str


_BASIC_INFO = TemplateInfo(
    BASIC_TEMPLATE,
    "Basic",
    "One column, standard headings, at most 2 pages. Reads well in the applicant tracking systems "
    "used in the US, UK, Canada and Australia.",
)

_TEMPLATES: dict[str, tuple[TemplateInfo, CVTemplate]] = {
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
    return [_BASIC_INFO, *(info for info, _ in _TEMPLATES.values())]


def has_template(template_id: str) -> bool:
    return template_id == BASIC_TEMPLATE or template_id in _TEMPLATES


def get_template(template_id: str) -> CVTemplate:
    entry = _TEMPLATES.get(template_id)
    if entry is None:
        raise NotFoundError(f"Template '{template_id}' not found")
    return entry[1]
