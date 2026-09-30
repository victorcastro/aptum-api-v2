from sqlalchemy.orm import Session

from aptum.core.exceptions import NotFoundError
from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.schemas import CVTemplateOut
from aptum.modules.cv.templates.registry import (
    DEFAULT_TEMPLATE,
    get_template,
    has_template,
    list_templates,
)
from aptum.modules.profile.models import Profile
from aptum.modules.profile.service import ProfileService


class CVService:
    def __init__(self, db: Session) -> None:
        self.profiles = ProfileService(db)

    def export_pdf(self, user_id: int, template_id: str | None = None) -> bytes:
        """Render the authenticated user's own profile; the profile is always resolved by user_id.
        An explicit template applies to this download only, without touching the saved preference."""
        profile = self.profiles.get_or_create(user_id)
        template = get_template(template_id or self._effective_template(profile))
        return template.render(build_cv_data(profile))

    def list_templates(self, user_id: int) -> list[CVTemplateOut]:
        effective = self._effective_template(self.profiles.get_or_create(user_id))
        return [
            CVTemplateOut(id=t.id, name=t.name, description=t.description, selected=t.id == effective)
            for t in list_templates()
        ]

    def set_preferred_template(self, user_id: int, template_id: str | None) -> list[CVTemplateOut]:
        if template_id is not None and not has_template(template_id):
            raise NotFoundError(f"Template '{template_id}' not found")
        profile = self.profiles.get_or_create(user_id)
        self.profiles.repository.update(profile, preferred_template=template_id)
        return self.list_templates(user_id)

    @staticmethod
    def _effective_template(profile: Profile) -> str:
        """Saved preference, or the default when unset or no longer registered."""
        saved = profile.preferred_template
        return saved if saved is not None and has_template(saved) else DEFAULT_TEMPLATE
