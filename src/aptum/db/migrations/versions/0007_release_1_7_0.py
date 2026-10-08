"""release 1.7.0: work preferences and timezone label on the profile

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-08 18:00:00.000000

- profiles.work_preferences (VARCHAR(16)[], NOT NULL, default {}): work modes the user is open
  to (remote, hybrid, onsite), checked against that closed set.
- profiles.timezone_label (VARCHAR(16), nullable): short label printed after the CV location.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from aptum.common.enums import WorkMode

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column(
            'work_preferences',
            postgresql.ARRAY(sa.String(length=16)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column('profiles', sa.Column('timezone_label', sa.String(length=16), nullable=True))
    allowed = ", ".join(f"'{mode.value}'" for mode in WorkMode)
    op.create_check_constraint(
        op.f('ck_profiles_work_preferences_allowed'),
        'profiles',
        f"work_preferences <@ ARRAY[{allowed}]::varchar[]",
    )


def downgrade() -> None:
    op.drop_constraint(op.f('ck_profiles_work_preferences_allowed'), 'profiles', type_='check')
    op.drop_column('profiles', 'timezone_label')
    op.drop_column('profiles', 'work_preferences')
