from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aptum.common.enums import UserRole
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

    def list_page(
        self, *, role: str | None, is_active: bool | None, email_query: str | None, limit: int, offset: int
    ) -> tuple[list[User], int]:
        query = select(User)
        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if email_query:
            query = query.where(User.email.icontains(email_query, autoescape=True))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.order_by(User.id).limit(limit).offset(offset)).all()
        return list(items), total

    def lock_active_admin_ids(self) -> list[int]:
        """Lock every active admin row (in id order, so concurrent callers never deadlock) and
        return their ids. Two admins demoting each other at once then serialize on these locks,
        so the "last active admin" check cannot be raced."""
        return list(
            self.db.scalars(
                select(User.id)
                .where(User.role == UserRole.admin.value, User.is_active.is_(True))
                .order_by(User.id)
                .with_for_update()
            )
        )

    def get_for_update(self, user_id: int) -> User | None:
        return self.db.scalars(select(User).where(User.id == user_id).with_for_update()).first()

    def get_by_email_for_update(self, email: str) -> User | None:
        return self.db.scalars(select(User).where(User.email == email).with_for_update()).first()

    def create(self, email: str, firebase_uid: str) -> User:
        """No commit. Flushes for the id; a duplicate email or uid raises IntegrityError here."""
        user = User(email=email, firebase_uid=firebase_uid)
        self.db.add(user)
        self.db.flush()
        return user

    def link_firebase_uid(self, user: User, firebase_uid: str) -> User:
        """No commit."""
        user.firebase_uid = firebase_uid
        return user
