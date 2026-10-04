"""Populate the local DB with a demo CV.

    uv run python -m aptum.db.seed [--firebase-uid <uid>] [--email you@example.com] [--reset] [--pdf cv.pdf] [--role admin]

Attaches the demo CV to the local user linked to that Firebase uid (default: the test user) (created if missing), so logging
in with that Firebase user shows the data. Pass --email with the Firebase user's email to keep it in sync. Refuses to touch a profile that already has CV data
unless --reset is passed. --role sets that user's role (audited, like the users CLI). Local development only.
"""

import argparse
from datetime import date

from sqlalchemy.orm import Session

from aptum.common.enums import (
    EmploymentType,
    ExperienceArea,
    LinkKind,
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
    ProfileLink,
    ProfileSkill,
    Project,
)
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.skills.categories import classify_skill
from aptum.modules.skills.models import Skill
from aptum.modules.users.admin_service import UserAdminService
from aptum.modules.users.models import User
from aptum.modules.users.repository import UserRepository

DEFAULT_EMAIL = "victor@castro.com"
DEFAULT_FIREBASE_UID = "Hez0o0kRJZbHuL5FBvYKD35RcK02"


def _company(db: Session, name: str, industry: str | None, *, consultancy: bool = False) -> Company:
    normalized = normalize_name(name)
    company = db.query(Company).filter(Company.normalized_name == normalized).first()
    if company is None:
        industry_row = db.query(Industry).filter(Industry.name == industry).first() if industry else None
        company = Company(
            name=name,
            normalized_name=normalized,
            industry_id=industry_row.id if industry_row else None,
            is_consultancy=consultancy,
        )
        db.add(company)
        db.flush()
    return company


def _skill(db: Session, name: str) -> Skill:
    slug = slugify(name)
    skill = db.query(Skill).filter(Skill.slug == slug).first()
    if skill is None:
        skill = Skill(name=name, slug=slug)
        db.add(skill)
        db.flush()
    return skill


def _get_user(db: Session, firebase_uid: str, email: str | None) -> User:
    users = UserRepository(db)
    user = users.get_by_firebase_uid(firebase_uid)
    if user is None:
        existing = users.get_by_email(email) if email else None
        if existing:
            return users.link_firebase_uid(existing, firebase_uid)
        return users.create(email or DEFAULT_EMAIL, firebase_uid)
    if email and user.email != email:
        if users.get_by_email(email) is not None:
            raise SystemExit(f"Another local user already has the email {email}.")
        user.email = email
        db.commit()
    return user


def _has_data(profile: Profile) -> bool:
    return any(
        (
            profile.experiences,
            profile.educations,
            profile.skills,
            profile.languages,
            profile.certifications,
            profile.projects,
            profile.links,
        )
    )


def seed(db: Session, firebase_uid: str, email: str | None, reset: bool) -> Profile:
    user = _get_user(db, firebase_uid, email)
    profile = ProfileRepository(db).get_by_user_id(user.id) or ProfileRepository(db).create(user.id)
    if _has_data(profile):
        if not reset:
            raise SystemExit("Profile already has CV data. Pass --reset to replace it.")
        for collection in (
            profile.experiences,
            profile.educations,
            profile.skills,
            profile.languages,
            profile.certifications,
            profile.projects,
            profile.links,
        ):
            collection.clear()
        db.flush()

    ntt = _company(db, "NTT Data", "Information Technology and Services", consultancy=True)
    bcp = _company(db, "Banco de Credito del Peru", "Banking")
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

    profile.first_name = "Ana"
    profile.last_name = "Torres"
    profile.headline = "Senior Backend Engineer"
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

    profile.links = [
        ProfileLink(kind=LinkKind.linkedin, url="https://linkedin.com/in/ana-torres-demo", label="LinkedIn"),
        ProfileLink(kind=LinkKind.github, url="https://github.com/ana-torres-demo", label="GitHub"),
    ]
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
    parser.add_argument("--firebase-uid", default=DEFAULT_FIREBASE_UID, help=f"Firebase uid of the test user (default {DEFAULT_FIREBASE_UID})")
    parser.add_argument("--email", help=f"Email of the Firebase user; sets/updates the local user (default {DEFAULT_EMAIL} on create)")
    parser.add_argument("--reset", action="store_true", help="Replace existing CV data of that profile")
    parser.add_argument("--pdf", metavar="PATH", help="Also write the rendered CV to this file")
    parser.add_argument("--role", choices=[role.value for role in UserRole], help="Also set the user's role")
    args = parser.parse_args()

    with SessionLocal() as db:
        profile = seed(db, args.firebase_uid, args.email, args.reset)
        print(f"Seeded demo CV for user_id={profile.user_id} (profile_id={profile.id})")
        if args.role:
            user = UserAdminService(db).set_role_by_operator(
                UserRepository(db).get_by_id(profile.user_id).email, UserRole(args.role)
            )
            print(f"Role of user_id={user.id} set to {user.role}")
        if args.pdf:
            with open(args.pdf, "wb") as file:
                file.write(render_cv_pdf(profile))
            print(f"PDF written to {args.pdf}")


if __name__ == "__main__":
    main()
