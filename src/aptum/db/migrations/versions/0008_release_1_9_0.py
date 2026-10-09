"""release 1.9.0: each profile's own skill categories

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-09 12:00:00.000000

- skill_categories (id, profile_id, name, position): the CV skill groups of one profile, which
  its owner creates, renames, reorders and deletes. Name unique per profile. `position` is the
  order the CV prints them. Deleting a profile deletes its categories.
- profile_skills.category_id (nullable, foreign key to skill_categories, SET NULL) replaces
  profile_skills.category (text with a CHECK on the six values). Null is `Other`, which is not a
  row and always prints last; deleting a category moves its skills there.
- Existing rows keep their group: each profile gets one category per group it used (except
  `Other`), positioned in the order of release 1.1.0, and category_id is filled by name.

Downgrade restores the text column and its CHECK. Names outside the six original values fold
into 'Other', since the old CHECK only allows those.
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
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['profile_id'], ['profiles.id'], name=op.f('fk_skill_categories_profile_id_profiles'), ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_skill_categories')),
        sa.UniqueConstraint('profile_id', 'name', name=op.f('uq_skill_categories_profile_id')),
    )
    op.create_index(op.f('ix_skill_categories_profile_id'), 'skill_categories', ['profile_id'])

    order = " ".join(f"WHEN '{name}' THEN {position}" for position, name in enumerate(CATEGORIES, 1))
    op.execute(
        "INSERT INTO skill_categories (profile_id, name, position) "
        f"SELECT DISTINCT profile_id, category, CASE category {order} END FROM profile_skills "
        f"WHERE category <> '{OTHER}'"
    )

    op.add_column('profile_skills', sa.Column('category_id', sa.Integer(), nullable=True))
    op.execute(
        "UPDATE profile_skills ps SET category_id = sc.id FROM skill_categories sc "
        "WHERE sc.profile_id = ps.profile_id AND sc.name = ps.category"
    )
    op.create_foreign_key(
        op.f('fk_profile_skills_category_id_skill_categories'),
        'profile_skills',
        'skill_categories',
        ['category_id'],
        ['id'],
        ondelete='SET NULL',
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
    op.drop_index(op.f('ix_skill_categories_profile_id'), table_name='skill_categories')
    op.drop_table('skill_categories')
