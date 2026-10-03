from factories import base_profile, profile_skill

from aptum.common.enums import SkillCategory
from aptum.modules.cv.ats.skills import select_skills, skill_lines


def test_without_offer_keeps_profile_order_and_caps_at_25():
    skills = [profile_skill(f"Skill {i}", position=i) for i in range(30)]
    selected = select_skills(list(reversed(skills)))
    assert [s.name for s in selected] == [f"Skill {i}" for i in range(25)]


def test_offer_relevant_skills_come_first_in_profile_order():
    profile = base_profile()
    offer = "AI Engineer. Must have AWS, retrieval-augmented generation and Python. Nice: Swift."
    names = [s.name for s in select_skills(profile.skills, offer)]
    assert names[:4] == ["Python", "RAG", "AWS", "Swift"]  # matched via name or alias, profile order
    assert set(names) == {ps.skill.name for ps in profile.skills}


def test_never_adds_skills_that_are_not_in_the_profile():
    profile = base_profile()
    offer = "Kubernetes, Terraform, LangChain, Go, Rust, PostgreSQL, Kafka and Python."
    names = {s.name for s in select_skills(profile.skills, offer)}
    assert names <= {ps.skill.name for ps in profile.skills}
    assert "Kubernetes" not in names and "LangChain" not in names


def test_offer_with_many_skills_keeps_relevant_within_limit():
    skills = [profile_skill(f"Tool{i}", position=i) for i in range(40)]
    offer = " ".join(f"Tool{i}" for i in range(30, 40))
    names = [s.name for s in select_skills(skills, offer)]
    assert len(names) == 25
    assert names[:10] == [f"Tool{i}" for i in range(30, 40)]


def test_ambiguous_words_do_not_count_as_skill_mentions():
    skills = [profile_skill("Go", 0), profile_skill("Swift", 1), profile_skill("Python", 2)]
    selected = select_skills(skills, "Join the rest of the team, go live fast with a swift delivery, Python.")
    assert [s.name for s in selected if s.offer_relevant] == ["Python"]


def test_duplicate_skill_names_are_listed_once():
    skills = [profile_skill("Docker", 0), profile_skill("docker", 1)]
    assert [s.name for s in select_skills(skills)] == ["Docker"]


def test_one_line_per_category_in_fixed_order():
    profile = base_profile()
    lines = [line.render() for line in skill_lines(select_skills(profile.skills))]
    assert lines == [
        "LLMs & AI: OpenAI API, RAG",
        "Backend: Python, FastAPI",
        "Cloud & DevOps: Docker, AWS",
        "Architecture: Hexagonal Architecture",
        "Mobile: Swift",
        "Other: Excel",
    ]


def test_stored_category_wins_over_dictionary():
    skill = profile_skill("Python", 0, category=SkillCategory.llms_ai.value)
    assert select_skills([skill])[0].category is SkillCategory.llms_ai
