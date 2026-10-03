from pydantic import BaseModel
from sqlalchemy.orm import Session

from aptum.core.exceptions import AptumError, ConflictError, NotFoundError
from aptum.db.base import Base
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.profile.models import (
    Certification,
    Education,
    Experience,
    Profile,
    ProfileLanguage,
    ProfileLink,
    ProfileSkill,
    Project,
)
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.profile.schemas import (
    ExperienceCreate,
    ExperienceUpdate,
    ProfileUpdate,
)
from aptum.modules.skills.categories import classify_skill
from aptum.modules.skills.repository import SkillRepository

_LABELS = {
    Experience: "Experience",
    Education: "Education",
    Certification: "Certification",
    Project: "Project",
    ProfileLink: "Link",
    ProfileLanguage: "Language",
    ProfileSkill: "Skill",
}

_ORDER = {
    Education: (Education.end_date.desc().nulls_first(), Education.id),
    Certification: (Certification.issue_date.desc().nulls_last(), Certification.id),
    Project: (Project.start_date.desc().nulls_last(), Project.id),
    ProfileLink: (ProfileLink.id,),
    ProfileLanguage: (ProfileLanguage.id,),
    ProfileSkill: (ProfileSkill.id,),
}

_DATE_RANGES = {
    Education: ("start_date", "end_date"),
    Project: ("start_date", "end_date"),
    Certification: ("issue_date", "expiration_date"),
}


class ProfileService:
    """Every operation takes the authenticated user's id and resolves their profile first,
    so a client can never reach another user's CV rows."""

    def __init__(self, db: Session) -> None:
        self.repository = ProfileRepository(db)
        self.companies = CompanyRepository(db)
        self.skills = SkillRepository(db)

    def get_or_create(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        return profile if profile is not None else self.repository.create(user_id)

    def update(self, user_id: int, data: ProfileUpdate) -> Profile:
        profile = self._get_owned(user_id)
        return self.repository.update(profile, **data.model_dump(exclude_unset=True))

    def list_experiences(self, user_id: int):
        profile = self._get_owned(user_id)
        return sorted(profile.experiences, key=lambda exp: (exp.start_date, exp.id), reverse=True)

    def add_experience(self, user_id: int, data: ExperienceCreate):
        profile = self._get_owned(user_id)
        self._check_companies(data.employer_id, data.client_id)
        return self.repository.add_experience(
            profile,
            is_current=data.end_date is None,
            **data.model_dump(),
        )

    def update_experience(self, user_id: int, experience_id: int, data: ExperienceUpdate):
        experience = self._get_owned_row(user_id, Experience, experience_id)
        fields = data.model_dump(exclude_unset=True)
        functions = fields.pop("functions", None)
        self._check_range(experience, fields, "start_date", "end_date")
        employer_id = fields.get("employer_id", experience.employer_id)
        client_id = fields.get("client_id", experience.client_id)
        if client_id is not None and client_id == employer_id:
            raise AptumError("client_id must differ from employer_id")
        self._check_companies(fields.get("employer_id"), fields.get("client_id"))
        if "end_date" in fields:
            fields["is_current"] = fields["end_date"] is None
        return self.repository.update_experience(experience, functions, **fields)

    def delete_experience(self, user_id: int, experience_id: int) -> None:
        self.delete_row(user_id, Experience, experience_id)

    def list_rows(self, user_id: int, model: type[Base]):
        profile = self._get_owned(user_id)
        return self.repository.list_rows(model, profile, *_ORDER[model])

    def add_row(self, user_id: int, model: type[Base], data: BaseModel):
        profile = self._get_owned(user_id)
        fields = data.model_dump()
        if model is ProfileLanguage and any(
            language.language_code == fields["language_code"] for language in profile.languages
        ):
            raise ConflictError("Language already added")
        if model is ProfileSkill:
            catalog_skill = self.skills.get(fields["skill_id"])
            if catalog_skill is None:
                raise NotFoundError("Skill not found")
            if any(skill.skill_id == fields["skill_id"] for skill in profile.skills):
                raise ConflictError("Skill already added")
            if fields.get("category") is None:
                fields["category"] = classify_skill(catalog_skill.name)
        return self.repository.add_row(model, profile, **fields)

    def update_row(self, user_id: int, model: type[Base], row_id: int, data: BaseModel):
        row = self._get_owned_row(user_id, model, row_id)
        fields = data.model_dump(exclude_unset=True)
        if model in _DATE_RANGES:
            self._check_range(row, fields, *_DATE_RANGES[model])
        if model is Education:
            self._check_range(row, fields, "start_year", "end_year")
        if model is ProfileSkill and "category" in fields and fields["category"] is None:
            fields["category"] = classify_skill(row.skill.name)
        return self.repository.update_row(row, **fields)

    def delete_row(self, user_id: int, model: type[Base], row_id: int) -> None:
        row = self._get_owned_row(user_id, model, row_id)
        self.repository.delete_row(row)

    def _check_companies(self, *company_ids: int | None) -> None:
        for company_id in set(company_ids) - {None}:
            if self.companies.get(company_id) is None:
                raise NotFoundError("Company not found")

    @staticmethod
    def _check_range(row, fields: dict, start_field: str, end_field: str) -> None:
        start = fields.get(start_field, getattr(row, start_field))
        end = fields.get(end_field, getattr(row, end_field))
        if start is not None and end is not None and end < start:
            raise AptumError(f"{end_field} must not be before {start_field}")

    def _get_owned_row(self, user_id: int, model: type[Base], row_id: int):
        profile = self._get_owned(user_id)
        row = self.repository.get_row(model, profile, row_id)
        if row is None:
            raise NotFoundError(f"{_LABELS[model]} not found")
        return row

    def _get_owned(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile
