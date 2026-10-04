from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from aptum.common.enums import UserRole
from aptum.db.base import Base, TimestampMixin
from aptum.db.constraints import in_values_check


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (in_values_check("role", UserRole),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(
        String(16), default=UserRole.user.value, server_default=UserRole.user.value
    )
