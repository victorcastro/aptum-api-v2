"""profile ATS fields: links, english level, work authorization, experience area, education years

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03 17:05:11.488080

Every new column is nullable (or has a constant default), so existing rows stay valid and
Postgres adds them without rewriting the tables. Downgrade drops them.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from aptum.common.enums import EnglishLevel, ExperienceArea, WorkAuthorization

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _in(column: str, values) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IS NULL OR {column} IN ({allowed})"


def upgrade() -> None:
    op.add_column('educations', sa.Column('start_year', sa.SmallInteger(), nullable=True))
    op.add_column('educations', sa.Column('end_year', sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        op.f('ck_educations_year_range'),
        'educations',
        "start_year IS NULL OR end_year IS NULL OR end_year >= start_year",
    )

    op.add_column('experiences', sa.Column('area', sa.String(length=16), nullable=True))
    op.create_check_constraint(op.f('ck_experiences_area_allowed'), 'experiences', _in('area', ExperienceArea))

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


def downgrade() -> None:
    op.drop_constraint(op.f('ck_profiles_work_authorization_allowed'), 'profiles', type_='check')
    op.drop_constraint(op.f('ck_profiles_english_level_allowed'), 'profiles', type_='check')
    op.drop_column('profiles', 'open_to_relocation')
    op.drop_column('profiles', 'work_authorization_country')
    op.drop_column('profiles', 'work_authorization')
    op.drop_column('profiles', 'english_level')
    op.drop_column('profiles', 'portfolio_url')
    op.drop_column('profiles', 'github_url')
    op.drop_column('profiles', 'linkedin_url')
    op.drop_constraint(op.f('ck_experiences_area_allowed'), 'experiences', type_='check')
    op.drop_column('experiences', 'area')
    op.drop_constraint(op.f('ck_educations_year_range'), 'educations', type_='check')
    op.drop_column('educations', 'end_year')
    op.drop_column('educations', 'start_year')
