"""release 1.10.0: education dates are years only

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-11 12:00:00.000000

- educations.start_date and educations.end_date are dropped together with their CHECK
  constraints. start_year and end_year stay as the only dates.
- Existing rows keep their dates: a missing year is filled from the month date before the drop.

Downgrade restores the columns empty, with the year of each row pinned to January 1st.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE educations SET "
        "start_year = COALESCE(start_year, EXTRACT(year FROM start_date)::int), "
        "end_year = COALESCE(end_year, EXTRACT(year FROM end_date)::int)"
    )
    op.drop_constraint(op.f('ck_educations_date_range'), 'educations', type_='check')
    op.drop_constraint(op.f('ck_educations_start_date_first_day'), 'educations', type_='check')
    op.drop_constraint(op.f('ck_educations_end_date_first_day'), 'educations', type_='check')
    op.drop_column('educations', 'start_date')
    op.drop_column('educations', 'end_date')


def downgrade() -> None:
    op.add_column('educations', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('educations', sa.Column('end_date', sa.Date(), nullable=True))
    op.execute(
        "UPDATE educations SET "
        "start_date = make_date(start_year, 1, 1), end_date = make_date(end_year, 1, 1)"
    )
    op.create_check_constraint(
        op.f('ck_educations_end_date_first_day'), 'educations', 'end_date IS NULL OR EXTRACT(day FROM end_date) = 1'
    )
    op.create_check_constraint(
        op.f('ck_educations_start_date_first_day'),
        'educations',
        'start_date IS NULL OR EXTRACT(day FROM start_date) = 1',
    )
    op.create_check_constraint(
        op.f('ck_educations_date_range'),
        'educations',
        'start_date IS NULL OR end_date IS NULL OR end_date >= start_date',
    )
