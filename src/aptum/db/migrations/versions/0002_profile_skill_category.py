"""profile_skills.category, backfilled from the skill dictionary

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03 11:00:00.000000

Adds the CV group of each profile skill. Existing rows are classified with the deterministic
dictionary in aptum/modules/skills/data/skill_dictionary.json; unknown skills stay "Other".
Downgrade drops the column (the category is derived data, nothing user-entered is lost).
"""
from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from aptum.common.enums import SkillCategory
from aptum.modules.skills.categories import classify_skill

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALLOWED = ", ".join(f"'{value}'" for value in SkillCategory)


def upgrade() -> None:
    # Constant default: Postgres fills existing rows without rewriting the table.
    op.add_column(
        'profile_skills',
        sa.Column('category', sa.String(length=40), server_default=SkillCategory.other.value, nullable=False),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT ps.id, s.name FROM profile_skills ps JOIN skills s ON s.id = ps.skill_id")
    ).all()
    ids_by_category: dict[str, list[int]] = defaultdict(list)
    for row_id, name in rows:
        category = classify_skill(name)
        if category is not SkillCategory.other:
            ids_by_category[category.value].append(row_id)
    for category, ids in ids_by_category.items():
        conn.execute(
            sa.text("UPDATE profile_skills SET category = :category WHERE id = ANY(:ids)"),
            {"category": category, "ids": ids},
        )

    op.create_check_constraint(
        op.f('ck_profile_skills_category_allowed'),
        'profile_skills',
        f"category IS NULL OR category IN ({_ALLOWED})",
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_profile_skills_category_allowed'), 'profile_skills', type_='check')
    op.drop_column('profile_skills', 'category')
