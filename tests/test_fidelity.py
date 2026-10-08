from datetime import date

from factories import base_profile

from aptum.modules.cv.ats.builder import build_ats_document
from aptum.modules.cv.ats.fidelity import (
    check_fidelity,
    enforce_fidelity,
    normalize_number,
    numbers_in,
    profile_facts,
)
from aptum.modules.cv.ats.keywords import keyword_coverage
from aptum.modules.cv.ats.pipeline import generate_ats_cv
from aptum.modules.cv.ats.years import years_of_experience

TODAY = date(2026, 10, 1)


def _setup():
    profile = base_profile()
    facts = profile_facts(profile, years_of_experience(profile.experiences, TODAY))
    return profile, facts, build_ats_document(profile)


def test_number_extraction_and_normalization():
    assert numbers_in("Served 12,000 users, cut 35% latency, 2x faster, 4.70 stars, S3 and EC2") == [
        "12000", "35", "2", "4.7",
    ]
    assert numbers_in("p95 down to 200ms on 5GB") == ["200", "5"]  # units do not hide a number
    assert normalize_number("1,5") == "1.5"


def test_generated_cv_from_profile_passes():
    profile, facts, doc = _setup()
    assert check_fidelity(doc, facts) == []
    assert generate_ats_cv(profile, "Python RAG", today=TODAY).fidelity_issues == []


def test_invented_number_in_bullet_is_removed():
    profile, facts, doc = _setup()
    doc.experiences[0].bullets.append("Grew revenue by 300% in 6 months.")
    warnings = []
    assert enforce_fidelity(doc, profile, facts, warnings) == []
    assert "Grew revenue by 300% in 6 months." not in doc.experiences[0].bullets
    assert [w.code for w in warnings] == ["fidelity_removed"]


def test_changed_employer_title_and_date_are_restored_from_profile():
    profile, facts, doc = _setup()
    exp = doc.experiences[1]
    exp.employer, exp.position, exp.start = "Globex", "Principal Architect", date(2017, 1, 1)
    issues = check_fidelity(doc, facts)
    assert {i.kind for i in issues} == {"employer", "title", "date"}
    assert enforce_fidelity(doc, profile, facts, []) == []
    assert (exp.employer, exp.position, exp.start) == ("Acme Consulting", "Backend Engineer", date(2019, 6, 1))


def test_normalized_comparison_accepts_case_and_accents():
    profile, facts, doc = _setup()
    profile.experiences[0].employer.name = "Nórthwind Labs"
    facts = profile_facts(profile, years_of_experience(profile.experiences, TODAY))
    doc.experiences[0].employer = "northwind labs"
    assert check_fidelity(doc, facts) == []


def test_unrepairable_parts_are_returned_as_issues():
    profile, facts, doc = _setup()
    exp = doc.experiences[0]
    exp.experience_id = None  # e.g. an LLM-written role we cannot trace back to a profile row
    exp.employer = "Initech"
    issues = enforce_fidelity(doc, profile, facts, [])
    assert [(i.kind, i.value) for i in issues] == [("employer", "Initech")]


def test_summary_sentence_with_invented_number_is_removed():
    profile, facts, doc = _setup()
    doc.summary = "Backend engineer. Led a team of 25 engineers."
    enforce_fidelity(doc, profile, facts, [])
    assert doc.summary == "Backend engineer."


def test_computed_years_are_allowed_numbers():
    profile = base_profile(summary=None)
    result = generate_ats_cv(profile, today=TODAY)
    assert "14+" in result.document.summary and result.fidelity_issues == []


def test_keyword_coverage_reports_missing_and_supported_without_adding():
    profile = base_profile()
    profile.skills = [ps for ps in profile.skills if ps.skill.name != "Docker"]  # still in a bullet
    offer = "We want Python, LLMs, Docker, Kubernetes and LangChain. The rest is a plus."
    result = generate_ats_cv(profile, offer, today=TODAY)
    coverage = result.keyword_coverage
    assert coverage.offer_keywords == ["LLMs", "LangChain", "Python", "Docker", "Kubernetes"]  # dictionary order
    assert "Python" in coverage.present_in_cv and "Docker" in coverage.present_in_cv  # via bullet
    assert set(coverage.missing) == {"Kubernetes", "LangChain"} | ({"LLMs"} - set(coverage.present_in_cv))
    assert "Kubernetes" not in result.document.plain_text()
    assert coverage.supported_by_profile == [k for k in coverage.missing if k == "LLMs"]


def test_keyword_supported_by_profile_but_trimmed_from_cv():
    profile = base_profile()
    doc = build_ats_document(profile)
    doc.skill_lines = []
    for exp in doc.experiences:
        exp.bullets = []
        exp.skills_line = None
    coverage = keyword_coverage("Swift and Docker", doc, profile)
    assert coverage.missing == ["Docker", "Swift"]
    assert coverage.supported_by_profile == ["Docker", "Swift"]
    assert coverage.coverage == 0.0


def test_no_offer_no_coverage():
    assert generate_ats_cv(base_profile(), today=TODAY).keyword_coverage is None


def test_invented_number_with_unit_is_caught():
    _, facts, doc = _setup()
    doc.experiences[0].bullets.append("Cut p95 latency to 80ms.")
    assert [(i.kind, i.value) for i in check_fidelity(doc, facts)] == [("number", "80")]
