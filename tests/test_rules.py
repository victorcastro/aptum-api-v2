import random
from datetime import date

from conftest import pdf_text
from factories import base_profile, experience

from aptum.modules.cv.ats import rules
from aptum.modules.cv.ats.builder import build_ats_document
from aptum.modules.cv.ats.pipeline import generate_ats_cv
from aptum.modules.cv.ats.years import years_of_experience
from aptum.modules.profile.checks import duplicate_educations
from aptum.modules.profile.models import Education

TODAY = date(2026, 10, 1)


def _codes(result) -> list[str]:
    return [w.code for w in result.warnings]


# --- Years claims ----------------------------------------------------------------------------


def test_summary_years_claim_is_corrected_to_computed_total():
    profile = base_profile(summary="Engineer with 20+ years of experience.")
    result = generate_ats_cv(profile, today=TODAY)
    assert result.document.summary == "Engineer with 14+ years of experience."
    assert "years_corrected" in _codes(result)


def test_true_years_claim_is_left_alone():
    profile = base_profile(summary="Engineer with 10+ years of experience.")
    result = generate_ats_cv(profile, today=TODAY)
    assert result.document.summary == "Engineer with 10+ years of experience."
    assert "years_corrected" not in _codes(result)


def test_area_claim_uses_per_area_figure():
    profile = base_profile(summary="5+ years in mobile development and 2 years in AI.")
    profile.experiences[0].area = "ai"
    profile.experiences[2].area = "mobile"
    result = generate_ats_cv(profile, today=TODAY)
    assert result.document.summary == "3+ years in mobile development and 2 years in AI."


def test_missing_summary_is_built_from_headline_and_computed_years_only():
    profile = base_profile(summary=None)
    profile.experiences[0].area = "ai"
    result = generate_ats_cv(profile, today=TODAY)
    assert result.document.summary == (
        "Senior Software Engineer with 14+ years of professional experience, including 3+ years in AI."
    )


def test_missing_summary_without_headline_is_a_warning():
    result = generate_ats_cv(base_profile(summary=None, headline=None), today=TODAY)
    assert result.document.summary is None
    assert "missing_summary" in _codes(result)


# --- Compression and page limit --------------------------------------------------------------


def test_roles_older_than_seven_years_are_compressed_recent_ones_untouched():
    profile = base_profile()
    profile.experiences[3].description = "Long description of an old job."
    doc = build_ats_document(profile)
    warnings = []
    rules.compress_old_roles(doc, TODAY, frozenset(), warnings)
    recent, old = doc.experiences[0], doc.experiences[3]
    assert not recent.compressed and len(recent.bullets) == 3
    assert old.compressed and len(old.bullets) <= 2 and old.description is None
    assert doc.experiences[2].compressed  # ended May 2019: more than 7 years before Oct 2026


_WORDS = ["ledger", "kiosk", "sensor", "pipeline", "cache", "tenant", "invoice", "webhook", "quota", "parser", "shard", "replica", "cohort", "beacon", "voucher", "gateway", "ticket", "audit", "locale", "badge", "cron", "metric", "router", "widget", "batch", "stream", "schema", "token", "vault", "lambda", "portal", "queue", "mapper", "digest", "crawler", "ranker", "bundle", "canary", "rollout", "payroll", "catalog", "checkout"]


def _long_profile():
    """13 roles x 8 distinct bullets (deterministic pseudo-random words), far beyond 2 pages."""
    profile = base_profile()
    rng = random.Random(7)
    profile.experiences = [
        experience(
            f"Engineer {i}",
            f"Company {i}",
            date(2000 + 2 * i, 1, 1),
            date(2001 + 2 * i, 12, 1) if i < 12 else None,
            [" ".join(rng.sample(_WORDS, 12)).capitalize() + f" for {i * 10 + j} teams." for j in range(8)],
        )
        for i in range(13)
    ]
    return profile


def test_two_page_limit_trims_bullets_but_never_drops_a_role():
    profile = _long_profile()
    result = generate_ats_cv(profile, today=TODAY)
    assert result.pages <= 2
    assert [e.position for e in result.document.experiences] == [f"Engineer {i}" for i in reversed(range(13))]
    text = pdf_text(result.pdf)
    assert all(f"Engineer {i} - Company {i}" in text for i in range(13))
    assert "trimmed_for_length" in _codes(result)
    newest = result.document.experiences[0]
    assert len(newest.bullets) == 8  # recent roles trimmed last


def test_oldest_bullets_are_trimmed_first():
    result = generate_ats_cv(_long_profile(), today=TODAY)
    trimmed_items = [w.item for w in result.warnings if w.code == "trimmed_for_length"]
    assert trimmed_items[0] == "Engineer 0 - Company 0"


# --- Duplicates and filler -------------------------------------------------------------------


def test_near_duplicate_bullets_across_roles_are_kept_once():
    result = generate_ats_cv(base_profile(), today=TODAY)
    bullets = [b for e in result.document.experiences for b in e.bullets]
    assert sum("FastAPI microservices handling 2 million" in b for b in bullets) == 1
    assert result.document.experiences[1].bullets[0].startswith("Designed FastAPI")  # kept in most recent role
    assert "duplicate_removed" in _codes(result)


def test_different_bullets_are_not_duplicates():
    assert rules.DUPLICATE_THRESHOLD > 0.5
    from aptum.modules.cv.ats.text import similarity

    assert similarity("Built a RAG assistant for support", "Migrated batch jobs to Docker on AWS") < 0.5
    assert similarity("Designed FastAPI services.", "designed fastapi services!") == 1.0


def test_filler_only_bullets_removed_and_filler_with_content_warned():
    profile = base_profile()
    profile.experiences[0].functions[2].description = "Responsible for migrating 40 services to Kubernetes clusters."
    result = generate_ats_cv(profile, today=TODAY)
    bullets = [b for e in result.document.experiences for b in e.bullets]
    assert "Collaborated with product, design and QA." not in bullets
    assert "Responsible for migrating 40 services to Kubernetes clusters." in bullets
    assert "filler_removed" in _codes(result) and "filler_phrase" in _codes(result)


def test_filler_list_is_read_from_config_file():
    phrases = rules.filler_phrases()
    assert "responsible for" in phrases
    assert "collaborated with product design and qa" in phrases


# --- Metrics ---------------------------------------------------------------------------------


def test_bullets_without_metrics_are_warned_not_invented():
    profile = base_profile()
    original = {f.description for e in profile.experiences for f in e.functions}
    result = generate_ats_cv(profile, today=TODAY)
    missing = [w for w in result.warnings if w.code == "missing_metric"]
    assert any(w.text == "Migrated batch jobs to Docker on AWS." for w in missing)
    assert all(w.suggestion and "metric" in w.suggestion for w in missing)
    bullets = {b for e in result.document.experiences for b in e.bullets}
    assert bullets <= original  # bullets are only ever removed, never rewritten


def test_duplicate_education_detection():
    a = Education(institution="Lakeside University", degree="BSc", field_of_study="Computer Science", is_active=True)
    b = Education(institution="lakeside  university", degree="Bachelor of Science in Computer Science", is_active=True)
    c = Education(institution="Lakeside University", degree="MBA", is_active=True)
    b.degree, b.field_of_study = "BSc", "Computer Science and Engineering"
    found = duplicate_educations([a, b, c])
    assert len(found) == 1 and found[0].institution == "Lakeside University"

    profile = base_profile()
    profile.educations.append(b)
    assert "duplicate_education" in _codes(generate_ats_cv(profile, today=TODAY))


def test_years_helper_matches_pipeline():
    profile = base_profile()
    assert generate_ats_cv(profile, today=TODAY).years == years_of_experience(profile.experiences, TODAY)


def test_area_claim_fails_when_area_experience_is_under_a_year():
    profile = base_profile(summary="Engineer with 5+ years in AI.")
    profile.experiences[0].start_date = date(2026, 4, 1)
    profile.experiences[0].area = "ai"
    result = generate_ats_cv(profile, today=TODAY)
    assert result.document.summary == "Engineer with 5+ years in AI."  # user text kept...
    assert "years_unsupported" in _codes(result)  # ...but reported, not validated against the total
