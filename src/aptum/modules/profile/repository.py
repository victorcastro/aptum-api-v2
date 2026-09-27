from sqlalchemy.orm import Session

from aptum.modules.profile.models import Education, Experience, Language, Profile


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

    def add_experience(self, profile: Profile, **fields) -> Experience:
        experience = Experience(profile_id=profile.id, **fields)
        self.db.add(experience)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def add_education(self, profile: Profile, **fields) -> Education:
        education = Education(profile_id=profile.id, **fields)
        self.db.add(education)
        self.db.commit()
        self.db.refresh(education)
        return education

    def add_language(self, profile: Profile, **fields) -> Language:
        language = Language(profile_id=profile.id, **fields)
        self.db.add(language)
        self.db.commit()
        self.db.refresh(language)
        return language
