from sqlalchemy.orm import Session

from aptum.modules.profile.models import Profile


class MatchingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile_embedding(self, user_id: int) -> list[float] | None:
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        return profile.embedding if profile else None
