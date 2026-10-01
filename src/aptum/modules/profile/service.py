from sqlalchemy.orm import Session

from aptum.core.exceptions import AptumError, ConflictError, NotFoundError
from aptum.modules.companies.repository import CompanyRepository
from aptum.modules.profile.models import Profile
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.profile.schemas import (
    CertificationCreate,
    CertificationUpdate,
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

    def set_experience_active(self, user_id: int, experience_id: int, is_active: bool):
        experience = self._get_owned_experience(user_id, experience_id)
        return self.repository.set_experience_active(experience, is_active)

    def delete_experience(self, user_id: int, experience_id: int) -> None:
        experience = self._get_owned_experience(user_id, experience_id)
        self.repository.delete_experience(experience)

    def add_education(self, user_id: int, data: EducationCreate):
        profile = self._get_owned(user_id)
        return self.repository.add_education(profile, **data.model_dump())

    def add_language(self, user_id: int, data: LanguageCreate):
        profile = self._get_owned(user_id)
        if self.repository.get_language(profile, data.language_code) is not None:
            raise ConflictError("Language already added")
        return self.repository.add_language(profile, **data.model_dump())

    def list_certifications(self, user_id: int):
        return self.repository.list_certifications(self._get_owned(user_id))

    def add_certification(self, user_id: int, data: CertificationCreate):
        profile = self._get_owned(user_id)
        return self.repository.add_certification(profile, **data.model_dump())

    def update_certification(self, user_id: int, certification_id: int, data: CertificationUpdate):
        certification = self._get_owned_certification(user_id, certification_id)
        fields = data.model_dump(exclude_unset=True)
        issue = fields.get("issue_date", certification.issue_date)
        expiration = fields.get("expiration_date", certification.expiration_date)
        if issue is not None and expiration is not None and expiration < issue:
            raise AptumError("expiration_date must not be before issue_date")
        return self.repository.update_certification(certification, **fields)

    def delete_certification(self, user_id: int, certification_id: int) -> None:
        certification = self._get_owned_certification(user_id, certification_id)
        self.repository.delete_certification(certification)

    def _get_owned_certification(self, user_id: int, certification_id: int):
        profile = self._get_owned(user_id)
        certification = self.repository.get_certification(profile, certification_id)
        if certification is None:
            raise NotFoundError("Certification not found")
        return certification

    def _get_owned_experience(self, user_id: int, experience_id: int):
        profile = self._get_owned(user_id)
        experience = self.repository.get_experience(profile, experience_id)
        if experience is None:
            raise NotFoundError("Experience not found")
        return experience

    def _get_owned(self, user_id: int) -> Profile:
        profile = self.repository.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile
