from sqlalchemy.orm import Session

from aptum.modules.profile.models import (
    Education,
    Experience,
    ExperienceFunction,
    Profile,
    ProfileLanguage,
)


class ProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_id(self, user_id: int) -> Profile | None:
        return self.db.query(Profile).filter(Profile.user_id == user_id).first()

    def create(self, user_id: int) -> Profile:
        profile = Profile(user_id=user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, profile: Profile, **fields) -> Profile:
        for key, value in fields.items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def set_embedding(self, profile: Profile, embedding: list[float]) -> Profile:
        profile.embedding = embedding
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def add_experience(self, profile: Profile, functions: list[str], **fields) -> Experience:
        experience = Experience(
            profile_id=profile.id,
            functions=[
                ExperienceFunction(description=text, position=index)
                for index, text in enumerate(functions)
            ],
            **fields,
        )
        self.db.add(experience)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def get_experience(self, profile: Profile, experience_id: int) -> Experience | None:
        return (
            self.db.query(Experience)
            .filter(Experience.id == experience_id, Experience.profile_id == profile.id)
            .first()
        )

    def set_experience_active(self, experience: Experience, is_active: bool) -> Experience:
        experience.is_active = is_active
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def delete_experience(self, experience: Experience) -> None:
        self.db.delete(experience)
        self.db.commit()

    def add_education(self, profile: Profile, **fields) -> Education:
        education = Education(profile_id=profile.id, **fields)
        self.db.add(education)
        self.db.commit()
        self.db.refresh(education)
        return education

    def get_language(self, profile: Profile, language_code: str) -> ProfileLanguage | None:
        return (
            self.db.query(ProfileLanguage)
            .filter(
                ProfileLanguage.profile_id == profile.id,
                ProfileLanguage.language_code == language_code,
            )
            .first()
        )

    def add_language(self, profile: Profile, **fields) -> ProfileLanguage:
        language = ProfileLanguage(profile_id=profile.id, **fields)
        self.db.add(language)
        self.db.commit()
        self.db.refresh(language)
        return language
