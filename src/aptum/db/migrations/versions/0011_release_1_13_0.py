"""release 1.13.0: moderators manage the degree catalog

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-21 12:00:00.000000

- Permission `degree:manage` (create, edit and delete degrees) is granted to the `moderator` role.
  `roles.sync` adds the permission row and gives it to `admin` on start, but never touches the
  grants of an existing role, so the moderator grant is made here. The permission row is created
  here too when missing; sync keeps its description.

Downgrade removes the grants and the permission.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CODE = 'degree:manage'
DESCRIPTION = 'Create, edit and delete degrees'


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (code, description) VALUES (:code, :description) ON CONFLICT (code) DO NOTHING"),
        {'code': CODE, 'description': DESCRIPTION},
    )
    conn.execute(
        sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'moderator' AND p.code = :code "
            "ON CONFLICT DO NOTHING"
        ),
        {'code': CODE},
    )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM permissions WHERE code = :code"), {'code': CODE})
