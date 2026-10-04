"""release 1.3.0: header links as one JSON column

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04 12:00:00.000000

- profiles.links (JSONB, NOT NULL, default []) holds the CV header links in print order:
  [{"kind", "label", "url", "visible"}]. It replaces profiles.linkedin_url, github_url and
  portfolio_url, which are copied into it (portfolio, linkedin, github) and then dropped.
- profile_links and the native enum link_kind are dropped. Their rows are not migrated.
  Downgrade recreates both empty and copies the first link of each kind back to the columns.
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

link_kind = sa.Enum('linkedin', 'github', 'portfolio', 'website', 'other', name='link_kind')

LABELS = {'portfolio': 'Portfolio', 'linkedin': 'LinkedIn', 'github': 'GitHub'}


def upgrade() -> None:
    op.add_column('profiles', sa.Column('links', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    bind = op.get_bind()
    rows = bind.execute(sa.text('SELECT id, portfolio_url, linkedin_url, github_url FROM profiles')).all()
    for profile_id, portfolio, linkedin, github in rows:
        links = [
            {'kind': kind, 'label': LABELS[kind], 'url': url, 'visible': True}
            for kind, url in (('portfolio', portfolio), ('linkedin', linkedin), ('github', github))
            if url
        ]
        if links:
            bind.execute(
                sa.text('UPDATE profiles SET links = CAST(:links AS jsonb) WHERE id = :id'),
                {'links': json.dumps(links), 'id': profile_id},
            )
    op.drop_column('profiles', 'portfolio_url')
    op.drop_column('profiles', 'github_url')
    op.drop_column('profiles', 'linkedin_url')
    op.drop_index(op.f('ix_profile_links_profile_id'), table_name='profile_links')
    op.drop_table('profile_links')
    link_kind.drop(bind, checkfirst=True)


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
    op.add_column('profiles', sa.Column('linkedin_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('github_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('portfolio_url', sa.String(length=500), nullable=True))
    for kind in ('linkedin', 'github', 'portfolio'):
        op.execute(
            f"UPDATE profiles SET {kind}_url = (SELECT elem->>'url' FROM jsonb_array_elements(links) AS elem "
            f"WHERE elem->>'kind' = '{kind}' LIMIT 1)"
        )
    op.drop_column('profiles', 'links')
