"""initial cv schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-28 18:53:47.822156
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
import pgvector.sqlalchemy


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDUSTRIES = [
    "Accounting",
    "Airlines and Aviation",
    "Automotive",
    "Banking",
    "Biotechnology",
    "Construction",
    "Consumer Goods",
    "Education",
    "Energy and Utilities",
    "Entertainment",
    "Financial Services",
    "Fintech",
    "Food and Beverage",
    "Government",
    "Healthcare",
    "Hospitality",
    "Human Resources",
    "Information Technology and Services",
    "Insurance",
    "Legal Services",
    "Logistics and Supply Chain",
    "Manufacturing",
    "Marketing and Advertising",
    "Media",
    "Mining and Metals",
    "Non-profit",
    "Oil and Gas",
    "Pharmaceuticals",
    "Real Estate",
    "Retail",
    "Software Development",
    "Telecommunications",
    "Tourism",
    "Transportation",
]

ENUM_TYPES = (
    "employment_type",
    "work_mode",
    "language_proficiency",
    "link_kind",
    "skill_level",
)


def _slug(name: str) -> str:
    return name.lower().replace(" and ", " ").replace(" ", "-")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    industries = op.create_table('industries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_industries')),
    sa.UniqueConstraint('name', name=op.f('uq_industries_name')),
    sa.UniqueConstraint('slug', name=op.f('uq_industries_slug'))
    )
    op.bulk_insert(industries, [{"name": n, "slug": _slug(n)} for n in INDUSTRIES])
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('firebase_uid', sa.String(length=128), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_firebase_uid'), 'users', ['firebase_uid'], unique=True)
    op.create_table('companies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('industry_id', sa.Integer(), nullable=True),
    sa.Column('city', sa.String(length=120), nullable=True),
    sa.Column('country_code', sa.String(length=2), nullable=True),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('logo_url', sa.String(length=500), nullable=True),
    sa.Column('is_consultancy', sa.Boolean(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_companies_created_by_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['industry_id'], ['industries.id'], name=op.f('fk_companies_industry_id_industries'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_companies')),
    sa.UniqueConstraint('normalized_name', name=op.f('uq_companies_normalized_name'))
    )
    op.create_index(op.f('ix_companies_industry_id'), 'companies', ['industry_id'], unique=False)
    op.create_table('profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(length=120), nullable=True),
    sa.Column('last_name', sa.String(length=120), nullable=True),
    sa.Column('headline', sa.String(length=255), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('phone', sa.String(length=40), nullable=True),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('city', sa.String(length=120), nullable=True),
    sa.Column('region', sa.String(length=120), nullable=True),
    sa.Column('country_code', sa.String(length=2), nullable=True),
    sa.Column('preferred_template', sa.String(length=40), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_profiles_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_profiles')),
    sa.UniqueConstraint('user_id', name=op.f('uq_profiles_user_id'))
    )
    op.create_table('skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('category', sa.String(length=80), nullable=True),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_skills_created_by_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_skills')),
    sa.UniqueConstraint('slug', name=op.f('uq_skills_slug'))
    )
    op.create_table('certifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('issuing_organization', sa.String(length=255), nullable=False),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('expiration_date', sa.Date(), nullable=True),
    sa.Column('credential_id', sa.String(length=255), nullable=True),
    sa.Column('credential_url', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('expiration_date IS NULL OR EXTRACT(day FROM expiration_date) = 1', name=op.f('ck_certifications_expiration_date_first_day')),
    sa.CheckConstraint('issue_date IS NULL OR EXTRACT(day FROM issue_date) = 1', name=op.f('ck_certifications_issue_date_first_day')),
    sa.CheckConstraint('issue_date IS NULL OR expiration_date IS NULL OR expiration_date >= issue_date', name=op.f('ck_certifications_date_range')),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_certifications_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_certifications'))
    )
    op.create_index(op.f('ix_certifications_profile_id'), 'certifications', ['profile_id'], unique=False)
    op.create_table('educations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('institution', sa.String(length=255), nullable=False),
    sa.Column('degree', sa.String(length=255), nullable=False),
    sa.Column('field_of_study', sa.String(length=255), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('grade', sa.String(length=80), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('end_date IS NULL OR EXTRACT(day FROM end_date) = 1', name=op.f('ck_educations_end_date_first_day')),
    sa.CheckConstraint('start_date IS NULL OR EXTRACT(day FROM start_date) = 1', name=op.f('ck_educations_start_date_first_day')),
    sa.CheckConstraint('start_date IS NULL OR end_date IS NULL OR end_date >= start_date', name=op.f('ck_educations_date_range')),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_educations_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_educations'))
    )
    op.create_index(op.f('ix_educations_profile_id'), 'educations', ['profile_id'], unique=False)
    op.create_table('experiences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.String(length=255), nullable=False),
    sa.Column('employer_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('employment_type', sa.Enum('full_time', 'part_time', 'contract', 'freelance', 'self_employed', 'internship', 'apprenticeship', 'temporary', name='employment_type'), nullable=True),
    sa.Column('work_mode', sa.Enum('remote', 'onsite', 'hybrid', name='work_mode'), nullable=True),
    sa.Column('location_city', sa.String(length=120), nullable=True),
    sa.Column('location_country_code', sa.String(length=2), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('end_date IS NULL OR EXTRACT(day FROM end_date) = 1', name=op.f('ck_experiences_end_date_first_day')),
    sa.CheckConstraint('is_current = (end_date IS NULL)', name=op.f('ck_experiences_is_current_matches_end_date')),
    sa.CheckConstraint('start_date IS NULL OR EXTRACT(day FROM start_date) = 1', name=op.f('ck_experiences_start_date_first_day')),
    sa.CheckConstraint('start_date IS NULL OR end_date IS NULL OR end_date >= start_date', name=op.f('ck_experiences_date_range')),
    sa.ForeignKeyConstraint(['client_id'], ['companies.id'], name=op.f('fk_experiences_client_id_companies'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['employer_id'], ['companies.id'], name=op.f('fk_experiences_employer_id_companies'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_experiences_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_experiences'))
    )
    op.create_index(op.f('ix_experiences_client_id'), 'experiences', ['client_id'], unique=False)
    op.create_index(op.f('ix_experiences_employer_id'), 'experiences', ['employer_id'], unique=False)
    op.create_index('ix_experiences_profile_id_start_date', 'experiences', ['profile_id', 'start_date'], unique=False)
    op.create_table('profile_languages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.String(length=2), nullable=False),
    sa.Column('proficiency', sa.Enum('elementary', 'limited_working', 'professional_working', 'full_professional', 'native_or_bilingual', name='language_proficiency'), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_profile_languages_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_profile_languages')),
    sa.UniqueConstraint('profile_id', 'language_code', name=op.f('uq_profile_languages_profile_id'))
    )
    op.create_table('profile_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('linkedin', 'github', 'portfolio', 'website', 'other', name='link_kind'), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=True),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_profile_links_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_profile_links'))
    )
    op.create_index(op.f('ix_profile_links_profile_id'), 'profile_links', ['profile_id'], unique=False)
    op.create_table('profile_skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.Column('level', sa.Enum('beginner', 'intermediate', 'advanced', 'expert', name='skill_level'), nullable=True),
    sa.Column('years_experience', sa.SmallInteger(), nullable=True),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_profile_skills_profile_id_profiles'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name=op.f('fk_profile_skills_skill_id_skills'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_profile_skills')),
    sa.UniqueConstraint('profile_id', 'skill_id', name=op.f('uq_profile_skills_profile_id'))
    )
    op.create_index(op.f('ix_profile_skills_skill_id'), 'profile_skills', ['skill_id'], unique=False)
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('url', sa.String(length=500), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('end_date IS NULL OR EXTRACT(day FROM end_date) = 1', name=op.f('ck_projects_end_date_first_day')),
    sa.CheckConstraint('start_date IS NULL OR EXTRACT(day FROM start_date) = 1', name=op.f('ck_projects_start_date_first_day')),
    sa.CheckConstraint('start_date IS NULL OR end_date IS NULL OR end_date >= start_date', name=op.f('ck_projects_date_range')),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_projects_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_projects'))
    )
    op.create_index(op.f('ix_projects_profile_id'), 'projects', ['profile_id'], unique=False)
    op.create_table('experience_functions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('experience_id', sa.Integer(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.id'], name=op.f('fk_experience_functions_experience_id_experiences'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_experience_functions'))
    )
    op.create_index(op.f('ix_experience_functions_experience_id'), 'experience_functions', ['experience_id'], unique=False)
    op.create_table('experience_skills',
    sa.Column('experience_id', sa.Integer(), nullable=False),
    sa.Column('skill_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['experience_id'], ['experiences.id'], name=op.f('fk_experience_skills_experience_id_experiences'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], name=op.f('fk_experience_skills_skill_id_skills'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('experience_id', 'skill_id', name=op.f('pk_experience_skills'))
    )
    op.create_index(op.f('ix_experience_skills_skill_id'), 'experience_skills', ['skill_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_experience_skills_skill_id'), table_name='experience_skills')
    op.drop_table('experience_skills')
    op.drop_index(op.f('ix_experience_functions_experience_id'), table_name='experience_functions')
    op.drop_table('experience_functions')
    op.drop_index(op.f('ix_projects_profile_id'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_profile_skills_skill_id'), table_name='profile_skills')
    op.drop_table('profile_skills')
    op.drop_index(op.f('ix_profile_links_profile_id'), table_name='profile_links')
    op.drop_table('profile_links')
    op.drop_table('profile_languages')
    op.drop_index('ix_experiences_profile_id_start_date', table_name='experiences')
    op.drop_index(op.f('ix_experiences_employer_id'), table_name='experiences')
    op.drop_index(op.f('ix_experiences_client_id'), table_name='experiences')
    op.drop_table('experiences')
    op.drop_index(op.f('ix_educations_profile_id'), table_name='educations')
    op.drop_table('educations')
    op.drop_index(op.f('ix_certifications_profile_id'), table_name='certifications')
    op.drop_table('certifications')
    op.drop_table('skills')
    op.drop_table('profiles')
    op.drop_index(op.f('ix_companies_industry_id'), table_name='companies')
    op.drop_table('companies')
    op.drop_index(op.f('ix_users_firebase_uid'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('industries')
    for enum_type in ENUM_TYPES:
        op.execute(f"DROP TYPE IF EXISTS {enum_type}")
