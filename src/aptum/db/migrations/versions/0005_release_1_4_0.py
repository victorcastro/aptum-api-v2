"""release 1.4.0: credential link toggle, education description removed

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05 12:00:00.000000

- certifications.show_credential_url (BOOLEAN, NOT NULL, default true) only controls the CV:
  the credential URL stays on the certification.
- profile_languages.is_active (BOOLEAN, NOT NULL, default true): inactive languages stay on the
  profile but are not printed on the CV.
- educations.description is dropped. Downgrade recreates it empty.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('certifications', sa.Column('show_credential_url', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('profile_languages', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.drop_column('educations', 'description')


def downgrade() -> None:
    op.add_column('educations', sa.Column('description', sa.Text(), nullable=True))
    op.drop_column('profile_languages', 'is_active')
    op.drop_column('certifications', 'show_credential_url')
