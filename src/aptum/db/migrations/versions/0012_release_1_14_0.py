"""release 1.14.0: experience areas frontend_web, frontend_mobile and fullstack

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-22 12:00:00.000000

- `experiences.area`: `mobile` becomes `frontend_mobile`; `frontend_web` and `fullstack` are new values.
  The allowed-values check is recreated and existing rows are updated.

Downgrade maps `frontend_mobile` back to `mobile` and the other new values to `other`.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHECK = "ck_experiences_area_allowed"
NEW_AREAS = ("backend", "frontend_web", "frontend_mobile", "fullstack", "ai", "other")
OLD_AREAS = ("backend", "mobile", "ai", "other")


def _check(areas: Sequence[str]) -> str:
    allowed = ", ".join(f"'{area}'" for area in areas)
    return f"area IS NULL OR area IN ({allowed})"


def upgrade() -> None:
    op.drop_constraint(op.f(CHECK), "experiences", type_="check")
    op.execute(sa.text("UPDATE experiences SET area = 'frontend_mobile' WHERE area = 'mobile'"))
    op.create_check_constraint(op.f(CHECK), "experiences", _check(NEW_AREAS))


def downgrade() -> None:
    op.drop_constraint(op.f(CHECK), "experiences", type_="check")
    op.execute(sa.text("UPDATE experiences SET area = 'mobile' WHERE area = 'frontend_mobile'"))
    op.execute(sa.text("UPDATE experiences SET area = 'other' WHERE area IN ('frontend_web', 'fullstack')"))
    op.create_check_constraint(op.f(CHECK), "experiences", _check(OLD_AREAS))
