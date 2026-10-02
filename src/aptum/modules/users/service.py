from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.users.models import User
from aptum.modules.users.repository import UserRepository


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.profiles = ProfileRepository(db)

    def get_or_create_from_firebase(self, firebase_uid: str, email: str) -> User:
        """Resolve the local user for a verified Firebase identity, creating it on first login."""
        user = self.repository.get_by_firebase_uid(firebase_uid)
        if user is not None:
            return user

        existing = self.repository.get_by_email(email)
        if existing is not None:
            return self.repository.link_firebase_uid(existing, firebase_uid)

        try:
            user = self.repository.create(email, firebase_uid)
        except IntegrityError:
            self.db.rollback()
            user = self.repository.get_by_firebase_uid(firebase_uid)
            if user is None:
                raise
            return user
        self.profiles.create(user.id)
        return user
