from sqlalchemy.orm import Session

from aptum.modules.profile.models import Profile


class MatchingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile(self, user_id: int) -> Profile | None:
        return self.db.query(Profile).filter(Profile.user_id == user_id).first()
