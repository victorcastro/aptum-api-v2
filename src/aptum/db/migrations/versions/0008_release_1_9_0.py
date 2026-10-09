"""release 1.9.0: editable skill categories

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-09 12:00:00.000000

- skill_categories (id, name unique, position, is_system): the CV skill groups, now rows instead
  of a fixed list. `position` is the order the CV prints them. Seeded with the six groups of
  release 1.1.0; `Other` is the system one (cannot be renamed or deleted) and takes the skills
  of a deleted category.
- profile_skills.category_id (NOT NULL, foreign key to skill_categories, RESTRICT) replaces
  profile_skills.category (text with a CHECK on the six values). Existing rows keep their group:
  category_id is filled by name.
- permission skill_category:manage is created by roles.sync, which gives it to admin.

Downgrade restores the text column and its CHECK. Categories created after the upgrade fold
into 'Other', since the old CHECK only allows the six original values.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = ("LLMs & AI", "Backend", "Cloud & DevOps", "Architecture", "Mobile", "Other")
OTHER = "Other"


def upgrade() -> None:
    op.create_table(
        'skill_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_skill_categories')),
        sa.UniqueConstraint('name', name=op.f('uq_skill_categories_name')),
    )
    categories = sa.table(
        'skill_categories',
        sa.column('name', sa.String),
        sa.column('position', sa.Integer),
        sa.column('is_system', sa.Boolean),
    )
    op.bulk_insert(
        categories,
        [{'name': name, 'position': position, 'is_system': name == OTHER} for position, name in enumerate(CATEGORIES, 1)],
    )

    op.add_column('profile_skills', sa.Column('category_id', sa.Integer(), nullable=True))
    op.execute(
        "UPDATE profile_skills ps SET category_id = sc.id FROM skill_categories sc WHERE sc.name = ps.category"
    )
    op.execute(
        f"UPDATE profile_skills SET category_id = (SELECT id FROM skill_categories WHERE name = '{OTHER}') "
        "WHERE category_id IS NULL"
    )
    op.alter_column('profile_skills', 'category_id', nullable=False)
    op.create_foreign_key(
        op.f('fk_profile_skills_category_id_skill_categories'),
        'profile_skills',
        'skill_categories',
        ['category_id'],
        ['id'],
        ondelete='RESTRICT',
    )
    op.create_index(op.f('ix_profile_skills_category_id'), 'profile_skills', ['category_id'])
    op.drop_constraint(op.f('ck_profile_skills_category_allowed'), 'profile_skills', type_='check')
    op.drop_column('profile_skills', 'category')


def downgrade() -> None:
    allowed = ", ".join(f"'{name}'" for name in CATEGORIES)
    op.add_column(
        'profile_skills',
        sa.Column('category', sa.String(length=40), server_default=OTHER, nullable=False),
    )
    op.execute(
        "UPDATE profile_skills ps SET category = sc.name FROM skill_categories sc "
        f"WHERE sc.id = ps.category_id AND sc.name IN ({allowed})"
    )
    op.create_check_constraint(
        op.f('ck_profile_skills_category_allowed'),
        'profile_skills',
        f"category IS NULL OR category IN ({allowed})",
    )
    op.drop_index(op.f('ix_profile_skills_category_id'), table_name='profile_skills')
    op.drop_constraint(op.f('fk_profile_skills_category_id_skill_categories'), 'profile_skills', type_='foreignkey')
    op.drop_column('profile_skills', 'category_id')
    op.drop_table('skill_categories')
