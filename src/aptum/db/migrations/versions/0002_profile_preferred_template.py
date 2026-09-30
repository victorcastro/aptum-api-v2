"""profile preferred template

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('profiles', sa.Column('preferred_template', sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column('profiles', 'preferred_template')
