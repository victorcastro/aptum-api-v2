from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aptum.modules.roles.models import PermissionRecord, Role
from aptum.modules.users.models import User


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_roles(self) -> list[Role]:
        return list(self.db.scalars(select(Role).order_by(Role.name)))

    def get(self, role_id: int) -> Role | None:
        return self.db.get(Role, role_id)

    def get_for_update(self, role_id: int) -> Role | None:
        """Locks the role row, so concurrent edits of the same role serialize."""
        return self.db.scalars(select(Role).where(Role.id == role_id).with_for_update()).first()

    def get_by_name(self, name: str) -> Role | None:
        return self.db.scalars(select(Role).where(Role.name == name)).first()

    def user_counts(self) -> dict[int, int]:
        """Users per role id; roles nobody has are missing."""
        rows = self.db.execute(select(User.role_id, func.count()).group_by(User.role_id))
        return {role_id: count for role_id, count in rows}

    def count_users(self, role_id: int) -> int:
        return self.db.scalar(select(func.count()).select_from(User).where(User.role_id == role_id)) or 0

    def create(self, name: str, description: str, permissions: list[PermissionRecord], *, is_system: bool = False) -> Role:
        """No commit. Flushes for the id; a duplicate name raises IntegrityError here."""
        role = Role(name=name, description=description, is_system=is_system, permissions=permissions)
        self.db.add(role)
        self.db.flush()
        return role

    def delete(self, role: Role) -> None:
        """No commit. Role permissions go with it (CASCADE); a role still assigned fails (RESTRICT)."""
        self.db.delete(role)

    def list_permissions(self) -> list[PermissionRecord]:
        return list(self.db.scalars(select(PermissionRecord).order_by(PermissionRecord.code)))

    def get_permissions(self, codes: Iterable[str]) -> list[PermissionRecord]:
        return list(
            self.db.scalars(
                select(PermissionRecord).where(PermissionRecord.code.in_(list(codes))).order_by(PermissionRecord.code)
            )
        )

    def create_permission(self, code: str, description: str) -> PermissionRecord:
        """No commit."""
        permission = PermissionRecord(code=code, description=description)
        self.db.add(permission)
        self.db.flush()
        return permission

    def delete_permission(self, permission: PermissionRecord) -> None:
        """No commit. Removed from every role too (CASCADE)."""
        self.db.delete(permission)
