"""Synthetic, in-memory CV profiles for tests. Every name, company and number here is made up.

Objects are transient ORM instances (never added to a session), so tests need no database.
"""

from datetime import date

from aptum.common.enums import LinkKind
from aptum.common.utils import normalize_name, slugify
from aptum.modules.commons.models import Language
from aptum.modules.companies.models import Company
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
from aptum.modules.skills.models import Skill

_ids = iter(range(1, 1_000_000))


def company(name: str) -> Company:
    return Company(id=next(_ids), name=name, normalized_name=normalize_name(name), is_consultancy=False)


def skill(name: str, category: str | None = None) -> Skill:
    return Skill(id=next(_ids), name=name, slug=slugify(name), category=category)


def profile_language(code: str, name: str, level: str) -> ProfileLanguage:
    return ProfileLanguage(id=next(_ids), language_code=code, language=Language(code=code, name=name), proficiency=level)


def profile_skill(name: str, **fields) -> ProfileSkill:
    s = skill(name)
    return ProfileSkill(id=next(_ids), skill_id=s.id, skill=s, **fields)


def experience(
    position: str,
    employer: str,
    start: date,
    end: date | None,
    bullets: list[str],
    *,
    client: str | None = None,
    skills: list[str] = (),
    **fields,
) -> Experience:
    employer_row = company(employer)
    client_row = company(client) if client else None
    return Experience(
        id=next(_ids),
        position=position,
        employer_id=employer_row.id,
        employer=employer_row,
        client_id=client_row.id if client_row else None,
        client=client_row,
        start_date=start,
        end_date=end,
        is_current=end is None,
        is_active=fields.pop("is_active", True),
        functions=[ExperienceFunction(description=text, position=i) for i, text in enumerate(bullets)],
        skills=[skill(name) for name in skills],
        **fields,
    )


def base_profile(**fields) -> Profile:
    """A mid-career engineer with backend, mobile and AI roles, overlapping dates and an old role."""
    defaults = {
        "first_name": "Alex",
        "last_name": "Rivera",
        "headline": "Senior Software Engineer",
        "summary": "Engineer building backend services and LLM features.",
        "phone": "+1 555 0100",
        "contact_email": "alex.rivera@example.com",
        "city": "Toronto",
        "region": "Ontario",
        "country_code": "CA",
    }
    profile = Profile(id=next(_ids), user_id=next(_ids), **{**defaults, **fields})
    profile.experiences = [
        experience(
            "AI Engineer",
            "Northwind Labs",
            date(2023, 1, 1),
            None,
            [
                "Built a RAG assistant with the OpenAI API and pgvector serving 12,000 monthly users.",
                "Reduced answer latency by 35% by caching embeddings.",
                "Responsible for code reviews.",
            ],
            skills=["Python", "OpenAI API", "RAG"],
        ),
        experience(
            "Backend Engineer",
            "Acme Consulting",
            date(2019, 6, 1),
            date(2023, 3, 1),
            [
                "Designed FastAPI microservices handling 2 million requests per day.",
                "Collaborated with product, design and QA.",
                "Migrated batch jobs to Docker on AWS.",
            ],
            client="Contoso Bank",
            skills=["FastAPI", "Docker", "AWS"],
        ),
        experience(
            "iOS Developer",
            "Fabrikam Mobile",
            date(2016, 2, 1),
            date(2019, 5, 1),
            [
                "Shipped a Swift banking app rated 4.7 stars.",
                "Designed FastAPI microservices handling 2 million requests per day!",
                "Maintained the release pipeline.",
            ],
            skills=["Swift"],
        ),
        experience(
            "Junior Developer",
            "Tailspin Toys",
            date(2012, 1, 1),
            date(2015, 12, 1),
            [
                "Wrote internal tools in Java.",
                "Supported the QA team during releases.",
                "Documented the deployment process.",
            ],
        ),
    ]
    profile.educations = [
        Education(
            id=next(_ids),
            institution="Lakeside University",
            degree="BSc",
            field_of_study="Computer Science",
            start_date=date(2008, 3, 1),
            end_date=date(2012, 12, 1),
            is_active=True,
        )
    ]
    profile.certifications = [
        Certification(
            id=next(_ids),
            name="Cloud Practitioner",
            issuing_organization="Example Cloud Institute",
            issue_date=date(2022, 5, 1),
            is_active=True,
        )
    ]
    profile.projects = [
        Project(id=next(_ids), name="Open-source CLI", description="A small CLI for prompt testing.", is_active=True)
    ]
    profile.links = [
        ProfileLink(id=next(_ids), kind=LinkKind.github, url="https://github.com/example-alex"),
        ProfileLink(id=next(_ids), kind=LinkKind.linkedin, url="https://www.linkedin.com/in/example-alex"),
    ]
    profile.languages = [
        profile_language("es", "Spanish", "Native"),
        profile_language("en", "English", "C1"),
    ]
    profile.skills = [
        profile_skill(name)
        for name in ["Python", "FastAPI", "OpenAI API", "RAG", "Docker", "AWS", "Swift", "Hexagonal Architecture", "Excel"]
    ]
    return profile
