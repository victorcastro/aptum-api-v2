"""release 1.1.0: skill categories, profile ATS fields, drop profile_skills.position

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03 11:00:00.000000

All schema changes of release 1.1.0 in one revision:

- profile_skills.category (NOT NULL, default 'Other', CHECK on allowed values), backfilled from
  the deterministic dictionary aptum/modules/skills/data/skill_dictionary.json.
- profiles: linkedin_url, github_url, portfolio_url, english_level, work_authorization,
  work_authorization_country, open_to_relocation (default false).
- experiences.area; educations.start_year / end_year.
- profile_skills.position dropped: the CV orders skills by evidence instead.

New columns are nullable or have a constant default, so existing rows stay valid and Postgres
adds them without rewriting the tables. Downgrade restores the 1.0.0 schema; position is
rebuilt from the creation order (id) of each profile's skills.
"""
from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from aptum.common.enums import (
    EnglishLevel,
    ExperienceArea,
    SkillCategory,
    WorkAuthorization,
)
from aptum.modules.skills.categories import classify_skill

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _in(column: str, values) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IS NULL OR {column} IN ({allowed})"


def _backfill_skill_categories() -> None:
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


def upgrade() -> None:
    # Skill categories
    op.add_column(
        'profile_skills',
        sa.Column('category', sa.String(length=40), server_default=SkillCategory.other.value, nullable=False),
    )
    _backfill_skill_categories()
    op.create_check_constraint(
        op.f('ck_profile_skills_category_allowed'), 'profile_skills', _in('category', SkillCategory)
    )
    op.drop_column('profile_skills', 'position')

    # Profile ATS fields
    op.add_column('profiles', sa.Column('linkedin_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('github_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('portfolio_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('english_level', sa.String(length=8), nullable=True))
    op.add_column('profiles', sa.Column('work_authorization', sa.String(length=32), nullable=True))
    op.add_column('profiles', sa.Column('work_authorization_country', sa.String(length=2), nullable=True))
    op.add_column(
        'profiles',
        sa.Column('open_to_relocation', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_check_constraint(
        op.f('ck_profiles_english_level_allowed'), 'profiles', _in('english_level', EnglishLevel)
    )
    op.create_check_constraint(
        op.f('ck_profiles_work_authorization_allowed'), 'profiles', _in('work_authorization', WorkAuthorization)
    )

    # Experience area
    op.add_column('experiences', sa.Column('area', sa.String(length=16), nullable=True))
    op.create_check_constraint(op.f('ck_experiences_area_allowed'), 'experiences', _in('area', ExperienceArea))

    # Education years
    op.add_column('educations', sa.Column('start_year', sa.SmallInteger(), nullable=True))
    op.add_column('educations', sa.Column('end_year', sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        op.f('ck_educations_year_range'),
        'educations',
        "start_year IS NULL OR end_year IS NULL OR end_year >= start_year",
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_educations_year_range'), 'educations', type_='check')
    op.drop_column('educations', 'end_year')
    op.drop_column('educations', 'start_year')

    op.drop_constraint(op.f('ck_experiences_area_allowed'), 'experiences', type_='check')
    op.drop_column('experiences', 'area')

    op.drop_constraint(op.f('ck_profiles_work_authorization_allowed'), 'profiles', type_='check')
    op.drop_constraint(op.f('ck_profiles_english_level_allowed'), 'profiles', type_='check')
    for column in (
        'open_to_relocation', 'work_authorization_country', 'work_authorization',
        'english_level', 'portfolio_url', 'github_url', 'linkedin_url',
    ):
        op.drop_column('profiles', column)

    op.add_column(
        'profile_skills', sa.Column('position', sa.SmallInteger(), server_default='0', nullable=False)
    )
    op.execute(
        "UPDATE profile_skills ps SET position = ranked.pos FROM ("
        " SELECT id, row_number() OVER (PARTITION BY profile_id ORDER BY id) - 1 AS pos FROM profile_skills"
        ") ranked WHERE ranked.id = ps.id"
    )
    op.alter_column('profile_skills', 'position', server_default=None)
    op.drop_constraint(op.f('ck_profile_skills_category_allowed'), 'profile_skills', type_='check')
    op.drop_column('profile_skills', 'category')
