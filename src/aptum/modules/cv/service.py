import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from aptum.common.utils import strip_accents
from aptum.core.exceptions import NotFoundError
from aptum.modules.cv.ats.pipeline import ATSResult, generate_ats_cv
from aptum.modules.cv.document import build_cv_data
from aptum.modules.cv.docx_render import render_cv_docx
from aptum.modules.cv.schemas import (
    ATSReport,
    CVSettingsRead,
    CVSettingsUpdate,
    CVTemplateOut,
    CVWarningOut,
    FidelityIssueOut,
    KeywordCoverageOut,
    SkillLineOut,
    YearsOfExperienceOut,
)
from aptum.modules.cv.templates.registry import (
    BASIC_TEMPLATE,
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

    def export_pdf(self, user_id: int, template_id: str | None = None) -> tuple[bytes, str]:
        """Render the authenticated user's own profile; the profile is always resolved by user_id.
        An explicit template applies to this download only, without touching the saved preference.
        Without one, the user's saved preference applies, or the default (basic) when unset.
        The basic template is rendered by the ATS pipeline. Returns the PDF bytes and the
        download filename."""
        profile = self.profiles.get_or_create(user_id)
        chosen = template_id if template_id is not None else self._effective_template(profile)
        if chosen == BASIC_TEMPLATE:
            result = generate_ats_cv(profile)
            return result.pdf, self._filename(result.document.full_name)
        template = get_template(chosen)
        doc = build_cv_data(profile)
        return template.render(doc), self._filename(doc.full_name)

    def export_docx(self, user_id: int) -> tuple[bytes, str]:
        """Editable Word CV of the authenticated user's own profile. Always the software-engineer
        layout, whatever template is saved. Returns the docx bytes and the download filename."""
        doc = build_cv_data(self.profiles.get_or_create(user_id))
        return render_cv_docx(doc), self._filename(doc.full_name, "docx")

    def generate_ats(self, user_id: int, job_description: str | None) -> tuple[ATSResult, str]:
        """ATS CV for the authenticated user's own profile, optionally tailored to a job offer."""
        profile = self.profiles.get_or_create(user_id)
        result = generate_ats_cv(profile, job_description)
        return result, self._filename(result.document.full_name)

    @staticmethod
    def report(result: ATSResult) -> ATSReport:
        coverage = result.keyword_coverage
        return ATSReport(
            page_count=result.pages,
            years_of_experience=YearsOfExperienceOut(total=result.years.total, by_area=result.years.by_area),
            skills=[SkillLineOut(category=line.category, names=list(line.names)) for line in result.document.skill_lines],
            warnings=[CVWarningOut(**vars(w)) for w in result.warnings],
            fidelity_issues=[FidelityIssueOut(**vars(i)) for i in result.fidelity_issues],
            keyword_coverage=KeywordCoverageOut(**vars(coverage), coverage=coverage.coverage) if coverage else None,
        )

    @staticmethod
    def _filename(full_name: str, extension: str = "pdf") -> str:
        """CV-YYYY.MM-First_Last-YYYYMMDDHHMMSS.<extension>, ASCII only so it is safe in a header."""
        now = datetime.now(UTC)
        ascii_name = strip_accents(full_name)
        name = "_".join(re.findall(r"[A-Za-z0-9]+", ascii_name)) or "CV"
        return f"CV-{now:%Y.%m}-{name}-{now:%Y%m%d%H%M%S}.{extension}"

    def list_templates(self, user_id: int) -> list[CVTemplateOut]:
        effective = self._effective_template(self.profiles.get_or_create(user_id))
        return [
            CVTemplateOut(id=t.id, name=t.name, description=t.description, selected=t.id == effective)
            for t in list_templates()
        ]

    def get_settings(self, user_id: int) -> CVSettingsRead:
        profile = self.profiles.get_or_create(user_id)
        return CVSettingsRead(template_id=self._effective_template(profile))

    def update_settings(self, user_id: int, data: CVSettingsUpdate) -> CVSettingsRead:
        fields = data.model_dump(exclude_unset=True)
        template_id = fields.get("template_id")
        if template_id is not None and not has_template(template_id):
            raise NotFoundError(f"Template '{template_id}' not found")
        profile = self.profiles.get_or_create(user_id)
        if "template_id" in fields:
            profile = self.profiles.set_preferred_template(profile, template_id)
        return CVSettingsRead(template_id=self._effective_template(profile))

    def reset_settings(self, user_id: int) -> None:
        """Back to defaults for every CV setting."""
        profile = self.profiles.get_or_create(user_id)
        self.profiles.set_preferred_template(profile, None)

    @staticmethod
    def _effective_template(profile: Profile) -> str:
        """Saved preference, or the default when unset or no longer registered."""
        saved = profile.preferred_template
        return saved if saved is not None and has_template(saved) else DEFAULT_TEMPLATE
