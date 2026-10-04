from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.enums import UserRole
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.roles.models import Role
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.users.models import User
from aptum.modules.users.repository import UserRepository


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.profiles = ProfileRepository(db)
        self.roles = RoleRepository(db)

    def default_role(self) -> Role:
        """The role every new user gets. Created by the migrations and kept by roles.sync."""
        role = self.roles.get_by_name(UserRole.user)
        if role is None:
            raise RuntimeError("Role 'user' is missing: run `python -m aptum.modules.roles.sync`")
        return role

    def get_or_create_from_firebase(self, firebase_uid: str, email: str) -> User:
        """Resolve the local user for a verified Firebase identity, creating it on first login."""
        user = self.repository.get_by_firebase_uid(firebase_uid)
        if user is not None:
            return user

        existing = self.repository.get_by_email(email)
        if existing is not None:
            self.repository.link_firebase_uid(existing, firebase_uid)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        try:
            user = self.repository.create(email, firebase_uid, self.default_role())
            self.profiles.create(user.id)  # same transaction: never a user without a profile
            self.db.commit()
        except IntegrityError:  # concurrent first login of the same user
            self.db.rollback()
            user = self.repository.get_by_firebase_uid(firebase_uid)
            if user is None:
                raise
            return user
        self.db.refresh(user)
        return user
