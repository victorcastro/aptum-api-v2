"""release 1.6.0: project link toggle, profile region removed

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-08 12:00:00.000000

- projects.show_url (BOOLEAN, NOT NULL, default true) only controls the CV: the project URL
  stays on the project.
- profiles.region is dropped: the CV location is city and country. Downgrade recreates it empty.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('show_url', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.drop_column('profiles', 'region')


def downgrade() -> None:
    op.add_column('profiles', sa.Column('region', sa.String(length=120), nullable=True))
    op.drop_column('projects', 'show_url')
