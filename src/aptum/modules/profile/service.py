from sqlalchemy.orm import Session

from aptum.core.exceptions import ConflictError, NotFoundError
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.profile.models import Profile
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.profile.schemas import (
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    ProfileUpdate,
)


class ProfileService:
    """Every operation takes the authenticated user's id and resolves their profile first,
    so a client can never reach another user's CV rows."""

    def __init__(self, db: Session) -> None:
        self.repository = ProfileRepository(db)
        self.companies = CompanyRepository(db)

    def get_or_create(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        return profile if profile is not None else self.repository.create(user_id)

    def update(self, user_id: int, data: ProfileUpdate) -> Profile:
        profile = self._get_owned(user_id)
        return self.repository.update(profile, **data.model_dump(exclude_unset=True))

    def add_experience(self, user_id: int, data: ExperienceCreate):
        profile = self._get_owned(user_id)
        for company_id in {data.employer_id, data.client_id} - {None}:
            if self.companies.get(company_id) is None:
                raise NotFoundError("Company not found")
        return self.repository.add_experience(
            profile,
            is_current=data.end_date is None,
            **data.model_dump(),
        )

    def delete_experience(self, user_id: int, experience_id: int) -> None:
        profile = self._get_owned(user_id)
        experience = self.repository.get_experience(profile, experience_id)
        if experience is None:
            raise NotFoundError("Experience not found")
        self.repository.delete_experience(experience)

    def add_education(self, user_id: int, data: EducationCreate):
        profile = self._get_owned(user_id)
        return self.repository.add_education(profile, **data.model_dump())

    def add_language(self, user_id: int, data: LanguageCreate):
        profile = self._get_owned(user_id)
        if self.repository.get_language(profile, data.language_code) is not None:
            raise ConflictError("Language already added")
        return self.repository.add_language(profile, **data.model_dump())

    def _get_owned(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile
