"""release 1.3.0: drop profile links

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04 12:00:00.000000

- profile_links and the native enum link_kind are dropped. LinkedIn, GitHub and portfolio
  live in profiles.linkedin_url, github_url and portfolio_url. The rows are not migrated.
  Downgrade recreates both empty.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

link_kind = sa.Enum('linkedin', 'github', 'portfolio', 'website', 'other', name='link_kind')


def upgrade() -> None:
    op.drop_index(op.f('ix_profile_links_profile_id'), table_name='profile_links')
    op.drop_table('profile_links')
    link_kind.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.create_table('profile_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('kind', link_kind, nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_profile_links_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_profile_links'))
    )
    op.create_index(op.f('ix_profile_links_profile_id'), 'profile_links', ['profile_id'], unique=False)
