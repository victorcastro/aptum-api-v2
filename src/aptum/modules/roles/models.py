from sqlalchemy import Boolean, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aptum.db.base import Base, TimestampMixin


class PermissionRecord(TimestampMixin, Base):
    """Mirror of `core.permissions.Permission`, kept in step by roles.sync. Named apart from the
    enum: the enum is what code checks, this row is what roles reference."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(String(255))


class Role(TimestampMixin, Base):
    """A named set of permissions. System roles (`user`, `moderator`, `admin`) are never deleted
    or renamed; `admin` always holds every permission."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="", server_default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    # Loaded with the role: every authenticated request reads them.
    permissions: Mapped[list[PermissionRecord]] = relationship(
        secondary="role_permissions", lazy="selectin", order_by=PermissionRecord.code
    )

    @property
    def permission_codes(self) -> frozenset[str]:
        return frozenset(permission.code for permission in self.permissions)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True, index=True
    )
