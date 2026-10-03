"""ATS CV generation: profile (+ optional job offer) -> document -> PDF, plus a report."""

from dataclasses import dataclass, field

from aptum.modules.cv.ats.builder import build_ats_document
from aptum.modules.cv.ats.document import ATSDocument
from aptum.modules.cv.ats.report import CVWarning
from aptum.modules.cv.templates.ats import ATSTemplate
from aptum.modules.profile.models import Profile


@dataclass
class ATSResult:
    document: ATSDocument
    pdf: bytes
    pages: int
    warnings: list[CVWarning] = field(default_factory=list)


def generate_ats_cv(profile: Profile, offer: str | None = None) -> ATSResult:
    document = build_ats_document(profile, offer)
    rendered = ATSTemplate().render(document)
    return ATSResult(document=document, pdf=rendered.content, pages=rendered.pages)
