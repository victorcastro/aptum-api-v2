from sqlalchemy.orm import Session

from aptum.core.exceptions import NotFoundError
from aptum.modules.profile.models import Profile
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.profile.schemas import (
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    ProfileUpdate,
)


class ProfileService:
    def __init__(self, db: Session) -> None:
        self.repository = ProfileRepository(db)

    def get_or_create(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        return profile if profile is not None else self.repository.create(user_id)

    def update(self, user_id: int, data: ProfileUpdate) -> Profile:
        profile = self._get_owned(user_id)
        return self.repository.update(profile, **data.model_dump(exclude_unset=True))

    def add_experience(self, user_id: int, data: ExperienceCreate):
        profile = self._get_owned(user_id)
        return self.repository.add_experience(profile, **data.model_dump())

    def add_education(self, user_id: int, data: EducationCreate):
        profile = self._get_owned(user_id)
        return self.repository.add_education(profile, **data.model_dump())

    def add_language(self, user_id: int, data: LanguageCreate):
        profile = self._get_owned(user_id)
        return self.repository.add_language(profile, **data.model_dump())

    def _get_owned(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile
