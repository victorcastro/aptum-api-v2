"""Populate the local DB with one test user per role and data to try what each role can do.

    uv run python -m aptum.db.seed_demo [--reset] [--pdf cv.pdf]

Local development only. Idempotent: rows are looked up by email, uid, slug or normalized name
before being created, so it can run again at any time.

- user@aptum.test (user): a full demo CV. Kept as is when the profile already has CV data,
  unless --reset replaces it.
- moderator@aptum.test (moderator): catalog rows to moderate. Skills with typos or duplicates
  ("Pyhton", "ReactJS"), a misspelled industry ("Bankng"), and companies created by the user:
  "Acme Startup" (unused: the user may edit it, a moderator may delete it) and "BCP" (used by
  the user's CV: the user gets 403 on edit, a moderator may edit it).
- admin@aptum.test (admin): "BCP" duplicates "Banco de Credito del Peru" and is in use, to
  merge. Two extra users without a Firebase account (one inactive) to change roles and status,
  and the role changes made here are already in the audit log. A custom role, "catalog_editor"
  (skills and industries only), to edit, assign or delete from /admin/roles.

Runs the roles sync first, as the container does on start, so permissions and system roles exist.

The three role users must exist in Firebase with these uids (and a verified email) to log in.
"""

import argparse
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from aptum.common.enums import (
    EmploymentType,
    ExperienceArea,
    SkillLevel,
    UserRole,
    WorkAuthorization,
    WorkMode,
)
from aptum.common.utils import normalize_name, slugify
from aptum.db.session import SessionLocal
from aptum.modules.companies.models import Company, Industry
from aptum.modules.cv.pdf import render_cv_pdf
from aptum.modules.profile.models import (
    Certification,
    Education,
    Experience,
    ExperienceFunction,
    Profile,
    ProfileLanguage,
    ProfileSkill,
    Project,
)
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.roles.sync import sync as sync_roles
from aptum.modules.skills.categories import classify_skill
from aptum.modules.skills.models import Skill
from aptum.modules.users.admin_service import UserAdminService
from aptum.modules.users.models import User
from aptum.modules.users.repository import UserRepository
from aptum.modules.users.service import UserService


@dataclass(frozen=True)
class SeedUser:
    role: UserRole
    email: str
    firebase_uid: str | None
    first_name: str
    last_name: str
    headline: str
    is_active: bool = True


# Firebase accounts of the test project. Admin first, so there is always an active admin.
ROLE_USERS = (
    SeedUser(UserRole.admin, "admin@aptum.test", "tNUaTkwhXOMHTdxxhUg9XgtO9ig2", "Lucia", "Vargas", "Platform Admin"),
    SeedUser(UserRole.moderator, "moderator@aptum.test", "nOkwOStcBocex7EHgeXkcdccKnm2", "Mateo", "Rojas", "Catalog Moderator"),
    SeedUser(UserRole.user, "user@aptum.test", "cO7ewzLE1tcCWEMsaEZCPyxUHts2", "Ana", "Torres", "Senior Backend Engineer"),
)  # fmt: skip

# No Firebase account: they only show up in /admin/users, to change their role or status.
EXTRA_USERS = (
    SeedUser(UserRole.user, "candidate@aptum.test", None, "Diego", "Paredes", "Data Engineer"),
    SeedUser(UserRole.user, "inactive@aptum.test", None, "Sofia", "Mendoza", "QA Engineer", is_active=False),
)


def _company(
    db: Session, name: str, industry: str | None, *, consultancy: bool = False, created_by: int | None = None
) -> Company:
    normalized = normalize_name(name)
    company = db.query(Company).filter(Company.normalized_name == normalized).first()
    if company is None:
        industry_row = db.query(Industry).filter(Industry.name == industry).first() if industry else None
        company = Company(
            name=name,
            normalized_name=normalized,
            industry_id=industry_row.id if industry_row else None,
            is_consultancy=consultancy,
            created_by_user_id=created_by,
        )
        db.add(company)
        db.flush()
    return company


def _skill(db: Session, name: str, created_by: int | None = None) -> Skill:
    slug = slugify(name)
    skill = db.query(Skill).filter(Skill.slug == slug).first()
    if skill is None:
        skill = Skill(name=name, slug=slug, created_by_user_id=created_by)
        db.add(skill)
        db.flush()
    return skill


def _industry(db: Session, name: str) -> Industry:
    slug = slugify(name)
    industry = db.query(Industry).filter(Industry.slug == slug).first()
    if industry is None:
        industry = Industry(name=name, slug=slug)
        db.add(industry)
        db.flush()
    return industry


def _user(db: Session, seed_user: SeedUser) -> User:
    """Find by Firebase uid, then by email (linking the uid), else create it with its profile."""
    users = UserRepository(db)
    user = users.get_by_firebase_uid(seed_user.firebase_uid) if seed_user.firebase_uid else None
    user = user or users.get_by_email(seed_user.email)
    if user is None:
        user = users.create(seed_user.email, seed_user.firebase_uid, UserService(db).default_role())
    else:
        user.email = seed_user.email
        user.firebase_uid = seed_user.firebase_uid or user.firebase_uid
    profiles = ProfileRepository(db)
    profile = profiles.get_by_user_id(user.id) or profiles.create(user.id)
    profile.first_name = profile.first_name or seed_user.first_name
    profile.last_name = profile.last_name or seed_user.last_name
    profile.headline = profile.headline or seed_user.headline
    db.commit()
    return user


def seed_users(db: Session) -> dict[str, User]:
    """Every seed user, by email. Roles go through the audited operator path (an entry only on a
    change); `is_active` is set directly, as a fixture."""
    admin = UserAdminService(db)
    seeded = {}
    for seed_user in (*ROLE_USERS, *EXTRA_USERS):
        user = _user(db, seed_user)
        user = admin.set_role_by_operator(user.email, seed_user.role)
        if user.is_active != seed_user.is_active:
            user.is_active = seed_user.is_active
            db.commit()
        seeded[user.email] = user
    return seeded


CUSTOM_ROLE = ("catalog_editor", "Fixes skills and industries", ("industry:manage", "skill:update_any"))


def seed_custom_role(db: Session) -> None:
    """An example custom role, left untouched once it exists."""
    roles = RoleRepository(db)
    name, description, codes = CUSTOM_ROLE
    if roles.get_by_name(name) is None:
        roles.create(name, description, roles.get_permissions(codes))
        db.commit()


def seed_catalog(db: Session, user: User) -> None:
    """Rows for the moderator to fix. "BCP" is created with the demo CV, which uses it."""
    _skill(db, "Pyhton", created_by=user.id)
    _skill(db, "ReactJS", created_by=user.id)
    _industry(db, "Bankng")
    _company(db, "Acme Startup", "Software Development", created_by=user.id)
    db.commit()


def _has_data(profile: Profile) -> bool:
    return any(
        (
            profile.experiences,
            profile.educations,
            profile.skills,
            profile.languages,
            profile.certifications,
            profile.projects,
        )
    )


def seed_demo_cv(db: Session, user: User, reset: bool) -> Profile | None:
    """The demo CV on the user's profile. None (nothing touched) when it already has CV data
    and `reset` is false."""
    profile = ProfileRepository(db).get_by_user_id(user.id)
    if _has_data(profile):
        if not reset:
            return None
        for collection in (
            profile.experiences,
            profile.educations,
            profile.skills,
            profile.languages,
            profile.certifications,
            profile.projects,
        ):
            collection.clear()
        db.flush()

    ntt = _company(db, "NTT Data", "Information Technology and Services", consultancy=True)
    _company(db, "Banco de Credito del Peru", "Banking")
    # Duplicate of the bank, created by the user and used below: the admin merges it.
    bcp = _company(db, "BCP", "Banking", created_by=user.id)
    rappi = _company(db, "Rappi", "Software Development")
    globant = _company(db, "Globant", "Information Technology and Services", consultancy=True)
    interbank = _company(db, "Interbank", "Banking")
    culqi = _company(db, "Culqi", "Software Development")
    telefonica = _company(db, "Telefonica del Peru", "Information Technology and Services")

    python, fastapi, postgres, docker, aws, react, java, redis, kafka = (
        _skill(db, "Python"),
        _skill(db, "FastAPI"),
        _skill(db, "PostgreSQL"),
        _skill(db, "Docker"),
        _skill(db, "AWS"),
        _skill(db, "React"),
        _skill(db, "Java"),
        _skill(db, "Redis"),
        _skill(db, "Kafka"),
    )

    profile.summary = (
        "Backend engineer with 8 years of experience building APIs and data platforms for "
        "banking and e-commerce. Focused on clean architecture, observability and mentoring."
    )
    profile.phone = "+51 999 888 777"
    profile.contact_email = "ana.torres@example.com"
    profile.city = "Lima"
    profile.country_code = "PE"
    profile.linkedin_url = "https://linkedin.com/in/ana-torres-demo"
    profile.github_url = "https://github.com/ana-torres-demo"
    profile.work_authorization = WorkAuthorization.requires_sponsorship
    profile.work_authorization_country = "CA"
    profile.open_to_relocation = True

    profile.experiences = [
        Experience(
            position="Senior Backend Engineer",
            employer_id=ntt.id,
            client_id=bcp.id,
            employment_type=EmploymentType.full_time,
            work_mode=WorkMode.hybrid,
            location_city="Lima",
            location_country_code="PE",
            start_date=date(2022, 3, 1),
            end_date=None,
            is_current=True,
            area=ExperienceArea.backend,
            description="Payments platform for a leading retail bank.",
            functions=[
                ExperienceFunction(description="Designed FastAPI services handling 2M transactions per day."),
                ExperienceFunction(description="Cut p95 latency by 40% with query tuning and caching."),
                ExperienceFunction(description="Mentored 4 engineers and led code reviews."),
            ],
            skills=[python, fastapi, postgres, docker],
        ),
        Experience(
            position="Software Engineer",
            employer_id=globant.id,
            client_id=interbank.id,
            employment_type=EmploymentType.full_time,
            work_mode=WorkMode.hybrid,
            location_city="Lima",
            location_country_code="PE",
            start_date=date(2020, 9, 1),
            end_date=date(2022, 2, 1),
            is_current=False,
            area=ExperienceArea.backend,
            description="Digital banking backend for a Peruvian bank.",
            functions=[
                ExperienceFunction(description="Built event-driven services with Kafka and Java."),
                ExperienceFunction(description="Introduced contract tests that removed release regressions."),
            ],
            skills=[java, kafka, postgres],
        ),
        Experience(
            position="Backend Developer",
            employer_id=rappi.id,
            employment_type=EmploymentType.full_time,
            work_mode=WorkMode.remote,
            location_country_code="PE",
            start_date=date(2018, 6, 1),
            end_date=date(2020, 8, 1),
            is_current=False,
            area=ExperienceArea.backend,
            functions=[
                ExperienceFunction(description="Built the order tracking API used by 5 countries."),
                ExperienceFunction(description="Migrated services to AWS with Docker and CI/CD."),
                ExperienceFunction(description="Added Redis caching that halved database load."),
            ],
            skills=[python, aws, docker, redis],
        ),
        Experience(
            position="Full Stack Developer",
            employer_id=culqi.id,
            employment_type=EmploymentType.part_time,
            work_mode=WorkMode.onsite,
            location_city="Lima",
            location_country_code="PE",
            start_date=date(2017, 1, 1),
            end_date=date(2018, 5, 1),
            is_current=False,
            area=ExperienceArea.other,
            description="Payment gateway for online merchants.",
            functions=[
                ExperienceFunction(description="Developed merchant dashboard screens in React."),
                ExperienceFunction(description="Implemented REST endpoints for payment reports."),
            ],
            skills=[python, react, postgres],
        ),
        Experience(
            position="Software Developer Intern",
            employer_id=telefonica.id,
            employment_type=EmploymentType.internship,
            work_mode=WorkMode.onsite,
            location_city="Lima",
            location_country_code="PE",
            start_date=date(2016, 1, 1),
            end_date=date(2016, 12, 1),
            is_current=False,
            area=ExperienceArea.other,
            functions=[
                ExperienceFunction(description="Automated internal reports with Python scripts."),
                ExperienceFunction(description="Fixed defects in a customer billing tool."),
            ],
            skills=[python, java],
        ),
    ]
    profile.educations = [
        Education(
            institution="Universidad Nacional de Ingenieria",
            degree="BSc",
            field_of_study="Computer Science",
            start_date=date(2013, 3, 1),
            end_date=date(2018, 12, 1),
        )
    ]
    profile.skills = [
        ProfileSkill(skill_id=python.id, category=classify_skill(python.name), level=SkillLevel.expert, years_experience=8),
        ProfileSkill(skill_id=fastapi.id, category=classify_skill(fastapi.name), level=SkillLevel.advanced, years_experience=4),
        ProfileSkill(skill_id=postgres.id, category=classify_skill(postgres.name), level=SkillLevel.advanced, years_experience=7),
        ProfileSkill(skill_id=docker.id, category=classify_skill(docker.name), level=SkillLevel.advanced, years_experience=6),
        ProfileSkill(skill_id=aws.id, category=classify_skill(aws.name), level=SkillLevel.intermediate, years_experience=4),
        ProfileSkill(skill_id=react.id, category=classify_skill(react.name), level=SkillLevel.beginner, years_experience=1),
    ]
    profile.languages = [
        ProfileLanguage(language_code="es", proficiency="Native"),
        ProfileLanguage(language_code="en", proficiency="C1"),
    ]
    profile.certifications = [
        Certification(
            name="AWS Certified Developer - Associate",
            issuing_organization="Amazon Web Services",
            issue_date=date(2023, 5, 1),
            expiration_date=date(2026, 5, 1),
        )
    ]
    profile.projects = [
        Project(
            name="Aptum API",
            description="Open CV platform with matching by industry and skills.",
            start_date=date(2025, 1, 1),
        )
    ]
    db.commit()
    db.refresh(profile)
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="Replace the demo CV of user@aptum.test")
    parser.add_argument("--pdf", metavar="PATH", help="Also write the demo CV to this file")
    args = parser.parse_args()

    with SessionLocal() as db:
        for line in sync_roles(db):
            print(f"roles sync: {line}")
        seed_custom_role(db)
        users = seed_users(db)
        for user in users.values():
            state = "active" if user.is_active else "inactive"
            print(f"user_id={user.id} {user.email} role={user.role_name} {state}")
        cv_user = users["user@aptum.test"]
        seed_catalog(db, cv_user)
        profile = seed_demo_cv(db, cv_user, args.reset)
        if profile is None:
            profile = ProfileRepository(db).get_by_user_id(cv_user.id)
            print("Demo CV already there (pass --reset to replace it)")
        else:
            print(f"Seeded demo CV for user_id={cv_user.id} (profile_id={profile.id})")
        if args.pdf:
            with open(args.pdf, "wb") as file:
                file.write(render_cv_pdf(profile))
            print(f"PDF written to {args.pdf}")


if __name__ == "__main__":
    main()
