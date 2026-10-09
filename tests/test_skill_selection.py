from datetime import date

from factories import base_profile, experience, profile_skill

from aptum.modules.cv.ats.skills import select_skills, skill_lines


def _names(selected) -> list[str]:
    return [s.name for s in selected]


def test_without_evidence_order_is_alphabetical_and_capped_at_25():
    skills = [profile_skill(f"Skill {i:02d}") for i in reversed(range(30))]
    assert _names(select_skills(skills)) == [f"Skill {i:02d}" for i in range(25)]


def test_recently_used_skills_come_first():
    profile = base_profile()
    names = _names(select_skills(profile.skills, experiences=profile.experiences))
    # current AI role (OpenAI API, Python, RAG) > Backend role ending 2023 (AWS, Docker, FastAPI)
    # > iOS role ending 2019 (Swift) > unused skills alphabetically
    assert names == [
        "OpenAI API", "Python", "RAG", "AWS", "Docker", "FastAPI", "Swift", "Excel", "Hexagonal Architecture",
    ]


def test_level_and_years_break_ties_before_alphabetical():
    skills = [
        profile_skill("Alpha"),
        profile_skill("Beta", level="intermediate"),
        profile_skill("Gamma", level="expert"),
        profile_skill("Delta", level="intermediate", years_experience=6),
    ]
    assert _names(select_skills(skills)) == ["Gamma", "Delta", "Beta", "Alpha"]


def test_recency_beats_level():
    old = experience("Dev", "A", date(2015, 1, 1), date(2016, 1, 1), [], skills=["Java"])
    new = experience("Dev", "B", date(2022, 1, 1), None, [], skills=["Go"])
    skills = [profile_skill("Java", level="expert"), profile_skill("Go", level="beginner")]
    assert _names(select_skills(skills, experiences=[old, new])) == ["Go", "Java"]


def test_inactive_experiences_are_not_evidence():
    hidden = experience("Dev", "A", date(2022, 1, 1), None, [], skills=["Zig"], is_active=False)
    skills = [profile_skill("Zig"), profile_skill("Ada")]
    assert _names(select_skills(skills, experiences=[hidden])) == ["Ada", "Zig"]


def test_offer_relevant_skills_come_first_then_evidence():
    profile = base_profile()
    offer = "AI Engineer. Must have AWS, retrieval-augmented generation and Python. Nice: Swift."
    names = _names(select_skills(profile.skills, offer, profile.experiences))
    assert names[:4] == ["Python", "RAG", "AWS", "Swift"]  # relevant, by recency
    assert names[4:] == ["OpenAI API", "Docker", "FastAPI", "Excel", "Hexagonal Architecture"]


def test_never_adds_skills_that_are_not_in_the_profile():
    profile = base_profile()
    offer = "Kubernetes, Terraform, LangChain, Go, Rust, PostgreSQL, Kafka and Python."
    names = set(_names(select_skills(profile.skills, offer, profile.experiences)))
    assert names <= {ps.skill.name for ps in profile.skills}
    assert "Kubernetes" not in names and "LangChain" not in names


def test_offer_with_many_skills_keeps_relevant_within_limit():
    skills = [profile_skill(f"Tool{i:02d}") for i in range(40)]
    offer = " ".join(f"Tool{i}" for i in range(30, 40))
    names = _names(select_skills(skills, offer))
    assert len(names) == 25
    assert names[:10] == [f"Tool{i}" for i in range(30, 40)]


def test_ambiguous_words_do_not_count_as_skill_mentions():
    skills = [profile_skill("Go"), profile_skill("Swift"), profile_skill("Python")]
    selected = select_skills(skills, "Join the rest of the team, go live fast with a swift delivery, Python.")
    assert [s.name for s in selected if s.offer_relevant] == ["Python"]


def test_duplicate_skill_names_are_listed_once():
    skills = [profile_skill("Docker"), profile_skill("docker")]
    assert len(select_skills(skills)) == 1


def test_one_line_per_category_in_fixed_order():
    profile = base_profile()
    lines = [line.render() for line in skill_lines(select_skills(profile.skills, experiences=profile.experiences))]
    assert lines == [
        "LLMs & AI: OpenAI API, RAG",
        "Backend: Python, FastAPI",
        "Cloud & DevOps: AWS, Docker",
        "Architecture: Hexagonal Architecture",
        "Mobile: Swift",
        "Other: Excel",
    ]


def test_selected_skill_carries_its_stored_category():
    skill = profile_skill("Python", category="LLMs & AI")
    assert select_skills([skill])[0].category.name == "LLMs & AI"


def test_dotnet_does_not_match_the_word_net():
    from aptum.modules.cv.ats.text import TextIndex
    assert not TextIndex("Strong focus on net income").find(".NET")
    assert TextIndex("Backend in C# and .NET 8").find(".NET")
