"""release 1.11.0: the profile location is the country only

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-12 12:00:00.000000

- profiles.city is dropped. The profile location is the country alone, printed on the CV
  as `Based in <country>`.
- profiles.available_immediately (boolean, default false) adds "Available immediately" to the CV header.
- profiles.country_code is renamed to profiles.based_in (still an ISO 3166-1 alpha-2 code).
- profiles.open_to_relocation is dropped: `relocation` is now one more value of work_preferences
  (the allowed values in its CHECK constraint grow from remote, onsite, hybrid to include it).
  Rows that had open_to_relocation set get `relocation` appended to their work_preferences.
- profile_skills.years_experience and profile_skills.level (with the skill_level enum type) are dropped.
  Which skills make the CV is decided by job offer and recent use; the group a skill is printed in comes
  from its category.
- profile_skills.position (integer, default 0): the order of the skills inside their category. Existing
  rows are numbered 1..n per profile and category by skill name.

Downgrade drops profile_skills.position and restores profile_skills.years_experience and profile_skills.level empty, drops available_immediately, restores profiles.city empty and the column name country_code,
and turns `relocation` in work_preferences back into open_to_relocation.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CHECK = op.f("ck_profiles_work_preferences_allowed")
OLD_MODES = ("remote", "onsite", "hybrid")
NEW_MODES = (*OLD_MODES, "relocation")
SKILL_LEVEL = sa.Enum("beginner", "intermediate", "advanced", "expert", name="skill_level")


def _allowed(modes: Sequence[str]) -> str:
    return ", ".join(f"'{mode}'" for mode in modes)


def upgrade() -> None:
    op.add_column("profile_skills", sa.Column("position", sa.Integer(), server_default="0", nullable=False))
    op.execute(
        "UPDATE profile_skills ps SET position = ranked.pos FROM ("
        "SELECT p.id, row_number() OVER (PARTITION BY p.profile_id, p.category_id "
        "ORDER BY lower(s.name), p.id) AS pos "
        "FROM profile_skills p JOIN skills s ON s.id = p.skill_id) ranked WHERE ranked.id = ps.id"
    )
    op.alter_column("profile_skills", "position", server_default=None)
    op.drop_column("profile_skills", "years_experience")
    op.drop_column("profile_skills", "level")
    SKILL_LEVEL.drop(op.get_bind(), checkfirst=True)
    op.drop_column("profiles", "city")
    op.alter_column("profiles", "country_code", new_column_name="based_in")
    op.add_column("profiles", sa.Column("available_immediately", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_constraint(CHECK, "profiles", type_="check")
    op.execute(
        "UPDATE profiles SET work_preferences = array_append(work_preferences, 'relocation') "
        "WHERE open_to_relocation"
    )
    op.drop_column("profiles", "open_to_relocation")
    op.create_check_constraint(CHECK, "profiles", f"work_preferences <@ ARRAY[{_allowed(NEW_MODES)}]::varchar[]")


def downgrade() -> None:
    op.drop_column("profile_skills", "position")
    SKILL_LEVEL.create(op.get_bind(), checkfirst=True)
    op.add_column("profile_skills", sa.Column("level", SKILL_LEVEL, nullable=True))
    op.add_column("profile_skills", sa.Column("years_experience", sa.SmallInteger(), nullable=True))
    op.drop_constraint(CHECK, "profiles", type_="check")
    op.add_column("profiles", sa.Column("open_to_relocation", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute("UPDATE profiles SET open_to_relocation = 'relocation' = ANY(work_preferences)")
    op.execute("UPDATE profiles SET work_preferences = array_remove(work_preferences, 'relocation')")
    op.create_check_constraint(CHECK, "profiles", f"work_preferences <@ ARRAY[{_allowed(OLD_MODES)}]::varchar[]")
    op.drop_column("profiles", "available_immediately")
    op.alter_column("profiles", "based_in", new_column_name="country_code")
    op.add_column("profiles", sa.Column("city", sa.String(length=120), nullable=True))
