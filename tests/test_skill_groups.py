from factories import profile_skill

from aptum.modules.profile.service import group_skills


def test_groups_follow_cv_category_order_skip_empty_ones_and_sort_skills_by_name():
    rows = [
        profile_skill("FastAPI", category="Backend", level="advanced", years_experience=4),
        profile_skill("LangChain", category="LLMs & AI"),
        profile_skill("Terraform", category="Cloud & DevOps"),
        profile_skill("django", category="Backend"),
        profile_skill("Celery", category="Backend"),
    ]
    result = group_skills(rows)

    assert result.total == 5
    assert [g.category.value for g in result.groups] == ["LLMs & AI", "Backend", "Cloud & DevOps"]
    assert [s.name for s in result.groups[1].skills] == ["Celery", "django", "FastAPI"]


def test_item_exposes_both_ids_and_flat_fields():
    row = profile_skill("FastAPI", category="Backend", level="advanced", years_experience=4)
    item = group_skills([row]).groups[0].skills[0]

    assert item.model_dump() == {
        "id": row.id,
        "skill_id": row.skill_id,
        "name": "FastAPI",
        "level": "advanced",
        "years_experience": 4,
    }
    assert item.id != item.skill_id


def test_no_skills_gives_an_empty_response():
    assert group_skills([]).model_dump() == {"total": 0, "groups": []}
