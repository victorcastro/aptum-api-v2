from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from aptum.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
