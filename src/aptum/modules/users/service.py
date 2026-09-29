from sqlalchemy.orm import Session

from aptum.core.exceptions import ConflictError, UnauthorizedError
from aptum.core.security import create_access_token, hash_password, verify_password
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.users.models import User
from aptum.modules.users.repository import UserRepository
from aptum.modules.users.schemas import UserCreate


class UserService:
    def __init__(self, db: Session) -> None:
        self.repository = UserRepository(db)
        self.profiles = ProfileRepository(db)

    def register(self, data: UserCreate) -> User:
        if self.repository.get_by_email(data.email) is not None:
            raise ConflictError("Email already registered")
        user = self.repository.create(data.email, hash_password(data.password))
        self.profiles.create(user.id)  # every user owns exactly one (initially empty) CV profile
        return user

    def authenticate(self, email: str, password: str) -> str:
        user = self.repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")
        return create_access_token(subject=str(user.id))
