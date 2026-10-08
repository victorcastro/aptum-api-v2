from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aptum.common.constants import EMBEDDING_DIM
from aptum.common.enums import (
    EmploymentType,
    ExperienceArea,
    SkillCategory,
    SkillLevel,
    WorkAuthorization,
    WorkMode,
)
from aptum.db.base import Base, TimestampMixin
from aptum.db.constraints import (
    date_range_check,
    in_values_check,
    month_precision_checks,
)
from aptum.modules.commons.models import Language
from aptum.modules.companies.models import Company
from aptum.modules.skills.models import Skill

_OWNED = {"cascade": "all, delete-orphan", "passive_deletes": True}


class Profile(TimestampMixin, Base):
    """Root of the CV. Every CV table hangs from here, and the profile belongs to one user."""

    __tablename__ = "profiles"
    __table_args__ = (
        in_values_check("work_authorization", WorkAuthorization),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    first_name: Mapped[str | None] = mapped_column(String(120), default=None)
    last_name: Mapped[str | None] = mapped_column(String(120), default=None)
    headline: Mapped[str | None] = mapped_column(String(255), default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    phone: Mapped[str | None] = mapped_column(String(40), default=None)
    contact_email: Mapped[str | None] = mapped_column(String(255), default=None)
    city: Mapped[str | None] = mapped_column(String(120), default=None)
    country_code: Mapped[str | None] = mapped_column(String(2), default=None)
    preferred_template: Mapped[str | None] = mapped_column(String(40), default=None)
    # Header links of the CV, in print order: [{"kind", "label", "url", "visible"}].
    # Validated by `ProfileLink` in the schemas; always written as a whole list.
    links: Mapped[list[dict]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    work_authorization: Mapped[str | None] = mapped_column(String(32), default=None)
    # Country the authorization (or the relocation target) refers to; ISO 3166-1 alpha-2.
    work_authorization_country: Mapped[str | None] = mapped_column(String(2), default=None)
    open_to_relocation: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="profile",
        order_by="Experience.start_date.desc()",
        **_OWNED,
    )
    educations: Mapped[list["Education"]] = relationship(
        back_populates="profile",
        order_by="Education.end_date.desc().nulls_first()",
        **_OWNED,
    )
    languages: Mapped[list["ProfileLanguage"]] = relationship(back_populates="profile", **_OWNED)
    skills: Mapped[list["ProfileSkill"]] = relationship(
        back_populates="profile", order_by="ProfileSkill.id", **_OWNED
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="profile", **_OWNED
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="profile", **_OWNED)


class ProfileLanguage(Base):
    __tablename__ = "profile_languages"
    __table_args__ = (UniqueConstraint("profile_id", "language_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    language_code: Mapped[str] = mapped_column(String(2), ForeignKey("languages.code"))
    # Code of a `language_levels` row: CEFR (A1-C2) or Native.
    proficiency: Mapped[str] = mapped_column(String(8), ForeignKey("language_levels.code"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    profile: Mapped["Profile"] = relationship(back_populates="languages")
    language: Mapped[Language] = relationship(lazy="joined")


class ProfileSkill(Base):
    __tablename__ = "profile_skills"
    __table_args__ = (
        UniqueConstraint("profile_id", "skill_id"),
        in_values_check("category", SkillCategory),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"), index=True)
    level: Mapped[SkillLevel | None] = mapped_column(
        Enum(SkillLevel, name="skill_level"), default=None
    )
    years_experience: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    # CV group. Set from the skill dictionary (skills/categories.py) unless the client sends one.
    category: Mapped[str] = mapped_column(
        String(40), default=SkillCategory.other.value, server_default=SkillCategory.other.value
    )

    profile: Mapped["Profile"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(lazy="joined")


class Experience(TimestampMixin, Base):
    """One position. `employer` is who hires; `client` is where the work happens, when
    hiring goes through a consultancy (e.g. employer NTT Data, client Banco BCP)."""

    __tablename__ = "experiences"
    __table_args__ = (
        date_range_check(),
        CheckConstraint("is_current = (end_date IS NULL)", name="is_current_matches_end_date"),
        *month_precision_checks("start_date", "end_date"),
        Index("ix_experiences_profile_id_start_date", "profile_id", "start_date"),
        in_values_check("area", ExperienceArea),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    position: Mapped[str] = mapped_column(String(255))
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), index=True
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), index=True, default=None
    )
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        Enum(EmploymentType, name="employment_type"), default=None
    )
    work_mode: Mapped[WorkMode | None] = mapped_column(Enum(WorkMode, name="work_mode"), default=None)
    location_city: Mapped[str | None] = mapped_column(String(120), default=None)
    location_country_code: Mapped[str | None] = mapped_column(String(2), default=None)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    is_current: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    description: Mapped[str | None] = mapped_column(Text, default=None)
    area: Mapped[str | None] = mapped_column(String(16), default=None)

    profile: Mapped["Profile"] = relationship(back_populates="experiences")
    employer: Mapped["Company"] = relationship(foreign_keys=[employer_id], lazy="joined")
    client: Mapped["Company | None"] = relationship(foreign_keys=[client_id], lazy="joined")
    functions: Mapped[list["ExperienceFunction"]] = relationship(
        back_populates="experience", order_by="ExperienceFunction.id", **_OWNED
    )
    skills: Mapped[list["Skill"]] = relationship(secondary="experience_skills")


class ExperienceFunction(Base):
    """One bullet of "functions in company"."""

    __tablename__ = "experience_functions"

    id: Mapped[int] = mapped_column(primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(Text)

    experience: Mapped["Experience"] = relationship(back_populates="functions")


class ExperienceSkill(Base):
    __tablename__ = "experience_skills"

    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True, index=True
    )


class Education(TimestampMixin, Base):
    __tablename__ = "educations"
    __table_args__ = (
        date_range_check(),
        *month_precision_checks("start_date", "end_date"),
        CheckConstraint(
            "start_year IS NULL OR end_year IS NULL OR end_year >= start_year", name="year_range"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    institution: Mapped[str] = mapped_column(String(255))
    degree: Mapped[str] = mapped_column(String(255))
    field_of_study: Mapped[str | None] = mapped_column(String(255), default=None)
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    # Year-only alternative for when the month is unknown; the CV prefers the month dates.
    start_year: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    end_year: Mapped[int | None] = mapped_column(SmallInteger, default=None)
    grade: Mapped[str | None] = mapped_column(String(80), default=None)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    profile: Mapped["Profile"] = relationship(back_populates="educations")


class Certification(TimestampMixin, Base):
    __tablename__ = "certifications"
    __table_args__ = (
        date_range_check("issue_date", "expiration_date"),
        *month_precision_checks("issue_date", "expiration_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    issuing_organization: Mapped[str] = mapped_column(String(255))
    issue_date: Mapped[date | None] = mapped_column(Date, default=None)
    expiration_date: Mapped[date | None] = mapped_column(Date, default=None)
    credential_id: Mapped[str | None] = mapped_column(String(255), default=None)
    credential_url: Mapped[str | None] = mapped_column(String(500), default=None)
    show_credential_url: Mapped[bool] = mapped_column(default=True, server_default=true())
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    profile: Mapped["Profile"] = relationship(back_populates="certifications")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (date_range_check(), *month_precision_checks("start_date", "end_date"))

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    url: Mapped[str | None] = mapped_column(String(500), default=None)
    show_url: Mapped[bool] = mapped_column(default=True, server_default=true())
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)

    profile: Mapped["Profile"] = relationship(back_populates="projects")
