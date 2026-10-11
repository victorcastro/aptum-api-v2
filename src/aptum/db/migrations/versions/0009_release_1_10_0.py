"""release 1.10.0: education dates are years only, no grade

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-11 12:00:00.000000

- educations.start_date and educations.end_date are dropped together with their CHECK
  constraints. start_year and end_year stay as the only dates.
- Existing rows keep their dates: a missing year is filled from the month date before the drop.
- educations.grade is dropped; the CV never printed it.
- educations.location_city and educations.location_country_code (nullable), like experiences.
- Degree catalog `degrees` (name, level, rank) and educations.degree_id (NOT NULL, RESTRICT)
  replace the free-text educations.degree. Each existing degree text is matched to the catalog
  ignoring case; texts that match nothing are added to the catalog under the level `Other`, so
  no education loses its degree.

Downgrade restores the date columns with the year of each row pinned to January 1st, grade
empty, and educations.degree with the name of each degree.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

DEGREES = (
    ("Technical and vocational", ("Technical Certificate", "Technical Diploma", "Advanced Technical Diploma", "Associate Degree")),
    (
        "Undergraduate",
        ("Bachelor's Degree", "Bachelor of Science", "Bachelor of Arts", "Bachelor of Engineering", "Professional Degree"),
    ),
    (
        "Postgraduate",
        (
            "Postgraduate Diploma",
            "Master's Degree",
            "Master of Science",
            "Master of Arts",
            "Master of Business Administration (MBA)",
            "Doctorate (PhD)",
        ),
    ),
    ("Other", ("Professional Certificate", "Bootcamp Certificate")),
)

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE educations SET "
        "start_year = COALESCE(start_year, EXTRACT(year FROM start_date)::int), "
        "end_year = COALESCE(end_year, EXTRACT(year FROM end_date)::int)"
    )
    op.drop_constraint(op.f('ck_educations_date_range'), 'educations', type_='check')
    op.drop_constraint(op.f('ck_educations_start_date_first_day'), 'educations', type_='check')
    op.drop_constraint(op.f('ck_educations_end_date_first_day'), 'educations', type_='check')
    op.drop_column('educations', 'start_date')
    op.drop_column('educations', 'end_date')
    op.drop_column('educations', 'grade')
    op.add_column('educations', sa.Column('location_city', sa.String(length=120), nullable=True))
    op.add_column('educations', sa.Column('location_country_code', sa.String(length=2), nullable=True))

    degrees = op.create_table(
        'degrees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('level', sa.String(length=40), nullable=False),
        sa.Column('rank', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_degrees')),
        sa.UniqueConstraint('name', name=op.f('uq_degrees_name')),
        sa.UniqueConstraint('rank', name=op.f('uq_degrees_rank')),
    )
    rows = [(level, name) for level, names in DEGREES for name in names]
    op.bulk_insert(
        degrees,
        [{'name': name, 'level': level, 'rank': rank} for rank, (level, name) in enumerate(rows, start=1)],
    )
    op.execute(
        "INSERT INTO degrees (name, level, rank) "
        "SELECT name, 'Other', (SELECT COALESCE(MAX(rank), 0) FROM degrees) + ROW_NUMBER() OVER (ORDER BY name) "
        "FROM (SELECT DISTINCT ON (lower(btrim(degree))) btrim(degree) AS name FROM educations "
        "WHERE lower(btrim(degree)) NOT IN (SELECT lower(name) FROM degrees) "
        'ORDER BY lower(btrim(degree)), btrim(degree) COLLATE "C") AS missing'
    )
    op.add_column('educations', sa.Column('degree_id', sa.Integer(), nullable=True))
    op.execute(
        "UPDATE educations SET degree_id = degrees.id FROM degrees "
        "WHERE lower(btrim(educations.degree)) = lower(degrees.name)"
    )
    op.alter_column('educations', 'degree_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        op.f('fk_educations_degree_id_degrees'), 'educations', 'degrees', ['degree_id'], ['id'], ondelete='RESTRICT'
    )
    op.create_index(op.f('ix_educations_degree_id'), 'educations', ['degree_id'], unique=False)
    op.drop_column('educations', 'degree')


def downgrade() -> None:
    op.add_column('educations', sa.Column('degree', sa.String(length=255), nullable=True))
    op.execute("UPDATE educations SET degree = degrees.name FROM degrees WHERE educations.degree_id = degrees.id")
    op.alter_column('educations', 'degree', existing_type=sa.String(length=255), nullable=False)
    op.drop_index(op.f('ix_educations_degree_id'), table_name='educations')
    op.drop_constraint(op.f('fk_educations_degree_id_degrees'), 'educations', type_='foreignkey')
    op.drop_column('educations', 'degree_id')
    op.drop_table('degrees')
    op.drop_column('educations', 'location_country_code')
    op.drop_column('educations', 'location_city')
    op.add_column('educations', sa.Column('grade', sa.String(length=80), nullable=True))
    op.add_column('educations', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('educations', sa.Column('end_date', sa.Date(), nullable=True))
    op.execute(
        "UPDATE educations SET "
        "start_date = make_date(start_year, 1, 1), end_date = make_date(end_year, 1, 1)"
    )
    op.create_check_constraint(
        op.f('ck_educations_end_date_first_day'), 'educations', 'end_date IS NULL OR EXTRACT(day FROM end_date) = 1'
    )
    op.create_check_constraint(
        op.f('ck_educations_start_date_first_day'),
        'educations',
        'start_date IS NULL OR EXTRACT(day FROM start_date) = 1',
    )
    op.create_check_constraint(
        op.f('ck_educations_date_range'),
        'educations',
        'start_date IS NULL OR end_date IS NULL OR end_date >= start_date',
    )
