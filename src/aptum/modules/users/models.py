from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aptum.common.enums import UserRole
from aptum.db.base import Base, TimestampMixin
from aptum.modules.roles.models import Role


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # RESTRICT: a role still assigned to someone cannot be deleted.
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True)

    # Joined with the user (and its permissions selected right after): authorization reads them
    # on every request.
    role: Mapped[Role] = relationship(lazy="joined", innerjoin=True)

    @property
    def role_name(self) -> str:
        return self.role.name

    @property
    def permissions(self) -> frozenset[str]:
        return self.role.permission_codes

    @property
    def is_admin(self) -> bool:
        return self.role.name == UserRole.admin
