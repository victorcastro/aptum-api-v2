from sqlalchemy.orm import Session

from aptum.modules.users.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        return self.db.query(User).filter(User.firebase_uid == firebase_uid).first()

    def create(self, email: str, firebase_uid: str) -> User:
        user = User(email=email, firebase_uid=firebase_uid)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def link_firebase_uid(self, user: User, firebase_uid: str) -> User:
        user.firebase_uid = firebase_uid
        self.db.commit()
        self.db.refresh(user)
        return user
