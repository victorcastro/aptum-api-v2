"""release 1.1.0: skill categories, profile ATS fields, language catalogs, user roles, audit log, drop profile_skills.position and experience_functions.position

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03 11:00:00.000000

All schema changes of release 1.1.0 in one revision:

- profile_skills.category (NOT NULL, default 'Other', CHECK on allowed values), backfilled from
  the deterministic dictionary aptum/modules/skills/data/skill_dictionary.json.
- skills.category dropped: free text the CV no longer reads (profile_skills.category replaces
  it). Downgrade restores it empty.
- profiles: linkedin_url, github_url, portfolio_url, work_authorization,
  work_authorization_country, open_to_relocation (default false).
- users.role ('user' | 'moderator' | 'admin', default 'user', CHECK on allowed values): RBAC;
  what each role may do lives in aptum/core/permissions.py, not in the database.
- audit_logs: append-only record of privileged changes (catalog moderation, role and active
  changes). actor_user_id is SET NULL on user delete; entity_id has no foreign key so entries
  outlive merged or deleted entities. changes is JSONB with before/after of changed fields.
- experiences.area; educations.start_year / end_year.
- profile_skills.position dropped: the CV orders skills by evidence instead.
- experience_functions.position dropped: responsibilities are raw content kept in insertion order (id).
- Language catalogs `languages` (ISO 639-1 code, English name) and `language_levels` (CEFR
  A1-C2 plus Native, ranked), seeded here. profile_languages.language_code and .proficiency
  become foreign keys to them; `proficiency` changes from the native enum
  `language_proficiency` to the level code: elementary -> A2, limited_working -> B1,
  professional_working -> B2, full_professional -> C1, native_or_bilingual -> Native.
  Language codes already stored but missing from the seed are added with the upper-cased code
  as name, so the foreign key never fails on existing data.

New columns are nullable or have a constant default, so existing rows stay valid and Postgres
adds them without rewriting the tables. Downgrade restores the 1.0.0 schema; position is
rebuilt from the creation order (id) of each profile's skills and of each experience's functions; language levels fold back as
A1/A2 -> elementary, B1 -> limited_working, B2 -> professional_working, C1/C2 ->
full_professional, Native -> native_or_bilingual.
"""
import json
from collections import defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from aptum.common.enums import (
    ExperienceArea,
    UserRole,
    WorkAuthorization,
)
from aptum.modules.skills.categories import DICTIONARY_PATH, skill_key

# The groups of release 1.1.0, frozen: release 1.9.0 moved them to the skill_categories table.
SKILL_CATEGORIES = ("LLMs & AI", "Backend", "Cloud & DevOps", "Architecture", "Mobile", "Other")

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEVELS = (
    ('A1', 'Beginner', 'Can use basic phrases and introduce themselves.'),
    ('A2', 'Elementary', 'Can handle simple, routine exchanges on familiar topics.'),
    ('B1', 'Intermediate', 'Can deal with most work and travel situations and describe experiences.'),
    ('B2', 'Upper intermediate', 'Can interact fluently with native speakers and write detailed texts on many topics.'),
    ('C1', 'Advanced', 'Can use the language flexibly and effectively for professional and academic purposes.'),
    ('C2', 'Proficient', 'Can understand virtually everything and express themselves precisely.'),
    ('Native', 'Native', 'Mother tongue.'),
)

LANGUAGES = {
    'af': 'Afrikaans', 'am': 'Amharic', 'ar': 'Arabic', 'az': 'Azerbaijani', 'be': 'Belarusian',
    'bg': 'Bulgarian', 'bn': 'Bengali', 'bs': 'Bosnian', 'ca': 'Catalan', 'cs': 'Czech',
    'cy': 'Welsh', 'da': 'Danish', 'de': 'German', 'el': 'Greek', 'en': 'English',
    'es': 'Spanish', 'et': 'Estonian', 'eu': 'Basque', 'fa': 'Persian', 'fi': 'Finnish',
    'fr': 'French', 'ga': 'Irish', 'gl': 'Galician', 'gn': 'Guarani', 'gu': 'Gujarati',
    'he': 'Hebrew', 'hi': 'Hindi', 'hr': 'Croatian', 'hu': 'Hungarian', 'hy': 'Armenian',
    'id': 'Indonesian', 'is': 'Icelandic', 'it': 'Italian', 'ja': 'Japanese', 'ka': 'Georgian',
    'kk': 'Kazakh', 'km': 'Khmer', 'kn': 'Kannada', 'ko': 'Korean', 'lt': 'Lithuanian',
    'lv': 'Latvian', 'mk': 'Macedonian', 'ml': 'Malayalam', 'mn': 'Mongolian', 'mr': 'Marathi',
    'ms': 'Malay', 'my': 'Burmese', 'nb': 'Norwegian Bokmål', 'ne': 'Nepali', 'nl': 'Dutch',
    'pa': 'Punjabi', 'pl': 'Polish', 'pt': 'Portuguese', 'qu': 'Quechua', 'ro': 'Romanian',
    'ru': 'Russian', 'sk': 'Slovak', 'sl': 'Slovenian', 'sq': 'Albanian', 'sr': 'Serbian',
    'sv': 'Swedish', 'sw': 'Swahili', 'ta': 'Tamil', 'te': 'Telugu', 'th': 'Thai',
    'tl': 'Tagalog', 'tr': 'Turkish', 'uk': 'Ukrainian', 'ur': 'Urdu', 'uz': 'Uzbek',
    'vi': 'Vietnamese', 'zh': 'Chinese',
}  # fmt: skip

OLD_TO_LEVEL = (
    ('elementary', 'A2'),
    ('limited_working', 'B1'),
    ('professional_working', 'B2'),
    ('full_professional', 'C1'),
    ('native_or_bilingual', 'Native'),
)
LEVEL_TO_OLD = (
    ('A1', 'elementary'),
    ('A2', 'elementary'),
    ('B1', 'limited_working'),
    ('B2', 'professional_working'),
    ('C1', 'full_professional'),
    ('C2', 'full_professional'),
    ('Native', 'native_or_bilingual'),
)
OLD_VALUES = ", ".join(f"'{old}'" for old, _ in OLD_TO_LEVEL)


def _case(column: str, pairs) -> str:
    whens = " ".join(f"WHEN '{source}' THEN '{target}'" for source, target in pairs)
    return f"CASE {column}::text {whens} END"


def _in(column: str, values) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IS NULL OR {column} IN ({allowed})"


def _dictionary_categories() -> dict[str, str]:
    """Skill key -> category, for every name and alias in the dictionary."""
    raw = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
    return {
        skill_key(term): category
        for category, items in raw["categories"].items()
        for item in items
        for term in (item["name"], *item.get("aliases", ()))
    }


def _backfill_skill_categories() -> None:
    by_key = _dictionary_categories()
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT ps.id, s.name FROM profile_skills ps JOIN skills s ON s.id = ps.skill_id")
    ).all()
    ids_by_category: dict[str, list[int]] = defaultdict(list)
    for row_id, name in rows:
        category = by_key.get(skill_key(name))
        if category is not None and category != "Other":
            ids_by_category[category].append(row_id)
    for category, ids in ids_by_category.items():
        conn.execute(
            sa.text("UPDATE profile_skills SET category = :category WHERE id = ANY(:ids)"),
            {"category": category, "ids": ids},
        )


def upgrade() -> None:
    # Roles (RBAC)
    op.add_column(
        'users', sa.Column('role', sa.String(length=16), server_default=UserRole.user.value, nullable=False)
    )
    op.create_check_constraint(op.f('ck_users_role_allowed'), 'users', _in('role', UserRole))

    # Audit log
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.BigInteger(), nullable=False),
        sa.Column('changes', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['actor_user_id'], ['users.id'], name=op.f('fk_audit_logs_actor_user_id_users'), ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs')),
    )
    op.create_index(op.f('ix_audit_logs_actor_user_id'), 'audit_logs', ['actor_user_id'])
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_entity_type_entity_id', 'audit_logs', ['entity_type', 'entity_id'])

    # Skill categories
    op.add_column(
        'profile_skills',
        sa.Column('category', sa.String(length=40), server_default='Other', nullable=False),
    )
    _backfill_skill_categories()
    op.create_check_constraint(
        op.f('ck_profile_skills_category_allowed'), 'profile_skills', _in('category', SKILL_CATEGORIES)
    )
    op.drop_column('skills', 'category')
    op.drop_column('profile_skills', 'position')
    op.drop_column('experience_functions', 'position')

    # Profile ATS fields
    op.add_column('profiles', sa.Column('linkedin_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('github_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('portfolio_url', sa.String(length=500), nullable=True))
    op.add_column('profiles', sa.Column('work_authorization', sa.String(length=32), nullable=True))
    op.add_column('profiles', sa.Column('work_authorization_country', sa.String(length=2), nullable=True))
    op.add_column(
        'profiles',
        sa.Column('open_to_relocation', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_check_constraint(
        op.f('ck_profiles_work_authorization_allowed'), 'profiles', _in('work_authorization', WorkAuthorization)
    )

    # Experience area
    op.add_column('experiences', sa.Column('area', sa.String(length=16), nullable=True))
    op.create_check_constraint(op.f('ck_experiences_area_allowed'), 'experiences', _in('area', ExperienceArea))

    # Education years
    op.add_column('educations', sa.Column('start_year', sa.SmallInteger(), nullable=True))
    op.add_column('educations', sa.Column('end_year', sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        op.f('ck_educations_year_range'),
        'educations',
        "start_year IS NULL OR end_year IS NULL OR end_year >= start_year",
    )

    # Language catalogs
    languages = op.create_table(
        'languages',
        sa.Column('code', sa.String(length=2), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint('code', name=op.f('pk_languages')),
        sa.UniqueConstraint('name', name=op.f('uq_languages_name')),
    )
    levels = op.create_table(
        'language_levels',
        sa.Column('code', sa.String(length=8), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('rank', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('code', name=op.f('pk_language_levels')),
        sa.UniqueConstraint('rank', name=op.f('uq_language_levels_rank')),
    )
    op.bulk_insert(languages, [{'code': code, 'name': name} for code, name in LANGUAGES.items()])
    op.bulk_insert(
        levels,
        [
            {'code': code, 'name': name, 'description': description, 'rank': rank}
            for rank, (code, name, description) in enumerate(LEVELS, start=1)
        ],
    )
    op.execute(
        "INSERT INTO languages (code, name) "
        "SELECT DISTINCT language_code, upper(language_code) FROM profile_languages "
        "WHERE language_code NOT IN (SELECT code FROM languages)"
    )

    # proficiency: native enum -> level code
    op.add_column('profile_languages', sa.Column('level', sa.String(length=8), nullable=True))
    op.execute(f"UPDATE profile_languages SET level = {_case('proficiency', OLD_TO_LEVEL)}")
    op.drop_column('profile_languages', 'proficiency')
    op.execute("DROP TYPE language_proficiency")
    op.alter_column('profile_languages', 'level', new_column_name='proficiency')
    op.alter_column('profile_languages', 'proficiency', existing_type=sa.String(length=8), nullable=False)
    op.create_foreign_key(
        op.f('fk_profile_languages_language_code_languages'),
        'profile_languages', 'languages', ['language_code'], ['code'],
    )
    op.create_foreign_key(
        op.f('fk_profile_languages_proficiency_language_levels'),
        'profile_languages', 'language_levels', ['proficiency'], ['code'],
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_constraint(op.f('ck_users_role_allowed'), 'users', type_='check')
    op.drop_column('users', 'role')

    op.drop_constraint(op.f('fk_profile_languages_proficiency_language_levels'), 'profile_languages', type_='foreignkey')
    op.drop_constraint(op.f('fk_profile_languages_language_code_languages'), 'profile_languages', type_='foreignkey')

    # proficiency: level code -> native enum
    op.execute(f"CREATE TYPE language_proficiency AS ENUM ({OLD_VALUES})")
    op.add_column(
        'profile_languages',
        sa.Column(
            'old_proficiency',
            sa.Enum(*(old for old, _ in OLD_TO_LEVEL), name='language_proficiency', create_type=False),
            nullable=True,
        ),
    )
    op.execute(
        f"UPDATE profile_languages SET old_proficiency = ({_case('proficiency', LEVEL_TO_OLD)})::language_proficiency"
    )
    op.drop_column('profile_languages', 'proficiency')
    op.alter_column('profile_languages', 'old_proficiency', new_column_name='proficiency', nullable=False)

    op.drop_table('language_levels')
    op.drop_table('languages')

    op.drop_constraint(op.f('ck_educations_year_range'), 'educations', type_='check')
    op.drop_column('educations', 'end_year')
    op.drop_column('educations', 'start_year')

    op.drop_constraint(op.f('ck_experiences_area_allowed'), 'experiences', type_='check')
    op.drop_column('experiences', 'area')

    op.drop_constraint(op.f('ck_profiles_work_authorization_allowed'), 'profiles', type_='check')
    for column in (
        'open_to_relocation', 'work_authorization_country', 'work_authorization',
        'portfolio_url', 'github_url', 'linkedin_url',
    ):
        op.drop_column('profiles', column)

    op.add_column(
        'profile_skills', sa.Column('position', sa.SmallInteger(), server_default='0', nullable=False)
    )
    op.execute(
        "UPDATE profile_skills ps SET position = ranked.pos FROM ("
        " SELECT id, row_number() OVER (PARTITION BY profile_id ORDER BY id) - 1 AS pos FROM profile_skills"
        ") ranked WHERE ranked.id = ps.id"
    )
    op.alter_column('profile_skills', 'position', server_default=None)
    op.add_column(
        'experience_functions', sa.Column('position', sa.SmallInteger(), server_default='0', nullable=False)
    )
    op.execute(
        "UPDATE experience_functions ef SET position = ranked.pos FROM ("
        " SELECT id, row_number() OVER (PARTITION BY experience_id ORDER BY id) - 1 AS pos"
        " FROM experience_functions) ranked WHERE ranked.id = ef.id"
    )
    op.alter_column('experience_functions', 'position', server_default=None)
    op.drop_constraint(op.f('ck_profile_skills_category_allowed'), 'profile_skills', type_='check')
    op.drop_column('profile_skills', 'category')
    op.add_column('skills', sa.Column('category', sa.String(length=80), nullable=True))
