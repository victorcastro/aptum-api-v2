"""ATS CV generation: profile (+ optional job offer) -> document -> PDF, plus a report.

Order: build from the profile, fix the summary's years claims, drop filler and duplicate
bullets, compress old roles, run the fidelity check, trim to the page limit, then collect
warnings and (with an offer) the keyword coverage of the final CV."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from aptum.modules.cv.ats import rules
from aptum.modules.cv.ats.builder import build_ats_document
from aptum.modules.cv.ats.document import ATSDocument
from aptum.modules.cv.ats.fidelity import FidelityIssue, enforce_fidelity, profile_facts
from aptum.modules.cv.ats.keywords import KeywordCoverage, keyword_coverage
from aptum.modules.cv.ats.report import CVWarning
from aptum.modules.cv.ats.years import YearsOfExperience, years_of_experience
from aptum.modules.cv.templates.ats import ATSTemplate
from aptum.modules.profile.checks import duplicate_educations
from aptum.modules.profile.models import Profile


@dataclass
class ATSResult:
    document: ATSDocument
    pdf: bytes
    pages: int
    years: YearsOfExperience
    warnings: list[CVWarning] = field(default_factory=list)
    fidelity_issues: list[FidelityIssue] = field(default_factory=list)
    keyword_coverage: KeywordCoverage | None = None


def generate_ats_cv(profile: Profile, offer: str | None = None, today: date | None = None) -> ATSResult:
    today = today or datetime.now(UTC).date()
    warnings: list[CVWarning] = []
    template = ATSTemplate()
    years = years_of_experience(profile.experiences, today)
    words = rules.offer_words(offer)

    document = build_ats_document(profile, offer)
    rules.apply_summary_rules(document, years, warnings)
    rules.remove_filler(document, warnings)
    rules.remove_duplicates(document, warnings)
    rules.compress_old_roles(document, today, words, warnings)
    fidelity_issues = enforce_fidelity(document, profile, profile_facts(profile, years), warnings)
    rules.enforce_page_limit(document, lambda doc: template.render(doc).pages, words, warnings)
    rules.metric_warnings(document, warnings)
    for duplicate in duplicate_educations(profile.educations):
        warnings.append(CVWarning(
            "duplicate_education",
            f"Possible duplicate education at {duplicate.institution}: "
            f"\"{duplicate.titles[0]}\" and \"{duplicate.titles[1]}\".",
            section="education",
            item=duplicate.institution,
            suggestion="Merge or deactivate one of them.",
        ))

    rendered = template.render(document)
    return ATSResult(
        document=document,
        pdf=rendered.content,
        pages=rendered.pages,
        years=years,
        warnings=warnings,
        fidelity_issues=fidelity_issues,
        keyword_coverage=keyword_coverage(offer, document, profile) if offer and offer.strip() else None,
    )
