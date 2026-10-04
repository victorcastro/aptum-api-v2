from sqlalchemy.orm import Session

from aptum.db.base import Base
from aptum.modules.profile.models import Experience, ExperienceFunction, Profile


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
            functions=_build_functions(functions),
            **fields,
        )
        self.db.add(experience)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def update_experience(
        self, experience: Experience, functions: list[str] | None, **fields
    ) -> Experience:
        for key, value in fields.items():
            setattr(experience, key, value)
        if functions is not None:
            experience.functions = _build_functions(functions)
        self.db.commit()
        self.db.refresh(experience)
        return experience

    def list_rows(self, model: type[Base], profile: Profile, *order_by) -> list:
        return (
            self.db.query(model)
            .filter(model.profile_id == profile.id)
            .order_by(*order_by)
            .all()
        )

    def get_row(self, model: type[Base], profile: Profile, row_id: int):
        return (
            self.db.query(model)
            .filter(model.id == row_id, model.profile_id == profile.id)
            .first()
        )

    def add_row(self, model: type[Base], profile: Profile, **fields):
        row = model(profile_id=profile.id, **fields)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_row(self, row, **fields):
        for key, value in fields.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_row(self, row) -> None:
        self.db.delete(row)
        self.db.commit()


def _build_functions(functions: list[str]) -> list[ExperienceFunction]:
    return [ExperienceFunction(description=text) for text in functions]
