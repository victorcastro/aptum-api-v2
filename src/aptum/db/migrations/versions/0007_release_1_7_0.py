"""release 1.7.0: profile region removed

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-08 18:00:00.000000

- profiles.region is dropped: the CV location is city and country. Downgrade recreates it empty.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column('profiles', 'region')


def downgrade() -> None:
    op.add_column('profiles', sa.Column('region', sa.String(length=120), nullable=True))
