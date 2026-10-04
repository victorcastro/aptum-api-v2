"""release 1.2.0: roles and permissions in tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-04 10:00:00.000000

- permissions (code unique, description): mirror of `core.permissions.Permission`. From now on
  `python -m aptum.modules.roles.sync` (run on every start, after the migrations) keeps it in
  line with the code; this revision only seeds the codes of release 1.2.0.
- roles (name unique, description, is_system) and role_permissions (CASCADE both ways). Seeded
  with the system roles `user`, `moderator`, `admin` and the grants that lived in code until
  1.1.0, plus the new `role:read` (moderator, admin) and `role:manage` (admin).
- users.role (string + CHECK) becomes users.role_id (FK to roles, RESTRICT, NOT NULL), backfilled
  by name, so every user keeps their role.

Seed values are literals on purpose: this revision must keep producing the same data even
after the enum changes. Downgrade folds users back to the role string; anyone holding a custom
role goes back to `user`.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
    ('audit:read', 'Read the audit log'),
    ('company:delete', 'Delete companies no experience uses'),
    ('company:merge', 'Merge duplicate companies'),
    ('company:update_any', 'Edit any company, even one in use'),
    ('industry:manage', 'Create and rename industries'),
    ('role:manage', 'Create, edit and delete roles'),
    ('role:read', 'List roles and permissions'),
    ('skill:update_any', 'Rename skills in the shared catalog'),
    ('user:deactivate', 'Activate and deactivate users'),
    ('user:list_read', 'List users'),
    ('user:manage_roles', "Change a user's role"),
)

MODERATOR = (
    'company:delete', 'company:update_any', 'industry:manage', 'role:read', 'skill:update_any',
    'user:list_read',
)  # fmt: skip

ROLES = (
    ('user', 'Every new user: manages their own CV', ()),
    ('moderator', 'Keeps the shared catalogs clean', MODERATOR),
    ('admin', 'Every permission, always', tuple(code for code, _ in PERMISSIONS)),
)

OLD_ROLES = ('user', 'moderator', 'admin')


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    ]


def upgrade() -> None:
    permissions = op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
        sa.UniqueConstraint('code', name=op.f('uq_permissions_code')),
    )
    roles = op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=32), nullable=False),
        sa.Column('description', sa.String(length=255), server_default='', nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default=sa.false(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('name', name=op.f('uq_roles_name')),
    )
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['permission_id'], ['permissions.id'], name=op.f('fk_role_permissions_permission_id_permissions'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['role_id'], ['roles.id'], name=op.f('fk_role_permissions_role_id_roles'), ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_role_permissions')),
    )
    op.create_index(op.f('ix_role_permissions_permission_id'), 'role_permissions', ['permission_id'])

    op.bulk_insert(permissions, [{'code': code, 'description': text} for code, text in PERMISSIONS])
    op.bulk_insert(roles, [{'name': name, 'description': text, 'is_system': True} for name, text, _ in ROLES])
    conn = op.get_bind()
    for name, _, codes in ROLES:
        if codes:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = :name AND p.code = ANY(:codes)"
                ),
                {'name': name, 'codes': list(codes)},
            )

    # users.role -> users.role_id, by name. The CHECK of 0002 guarantees every name exists.
    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))
    op.execute("UPDATE users SET role_id = roles.id FROM roles WHERE roles.name = users.role")
    op.alter_column('users', 'role_id', existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'])
    op.create_foreign_key(
        op.f('fk_users_role_id_roles'), 'users', 'roles', ['role_id'], ['id'], ondelete='RESTRICT'
    )
    op.drop_constraint(op.f('ck_users_role_allowed'), 'users', type_='check')
    op.drop_column('users', 'role')


def downgrade() -> None:
    op.add_column(
        'users', sa.Column('role', sa.String(length=16), server_default='user', nullable=False)
    )
    allowed = ", ".join(f"'{name}'" for name in OLD_ROLES)
    op.execute(
        "UPDATE users SET role = roles.name FROM roles "
        f"WHERE roles.id = users.role_id AND roles.name IN ({allowed})"
    )
    op.create_check_constraint(op.f('ck_users_role_allowed'), 'users', f"role IS NULL OR role IN ({allowed})")
    op.drop_constraint(op.f('fk_users_role_id_roles'), 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_column('users', 'role_id')

    op.drop_index(op.f('ix_role_permissions_permission_id'), table_name='role_permissions')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
