from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity, UserRole
from aptum.common.pagination import PageParams
from aptum.core.exceptions import ConflictError, NotFoundError
from aptum.core.permissions import Actor
from aptum.modules.audit.service import AuditService
from aptum.modules.roles.models import Role
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.users.models import User
from aptum.modules.users.policy import (
    check_active_change,
    check_role_change,
    is_last_active_admin,
)
from aptum.modules.users.repository import UserRepository


class UserAdminService:
    """Role and status management. Every change is checked by users/policy.py and audited in
    the same transaction."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UserRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    def list_page(
        self, page: PageParams, *, role: str | None, is_active: bool | None, email_query: str | None
    ) -> tuple[list[User], int]:
        return self.repository.list_page(
            role=role, is_active=is_active, email_query=email_query, limit=page.limit, offset=page.offset
        )

    def _locked_target(self, user_id: int) -> tuple[User, int]:
        # Admin rows first, then the target, always in this order.
        active_admins = len(self.repository.lock_active_admin_ids())
        target = self.repository.get_for_update(user_id)
        if target is None:
            raise NotFoundError("User not found")
        return target, active_admins

    def _role(self, name: str) -> Role:
        role = self.roles.get_by_name(name)
        if role is None:
            raise NotFoundError("Role not found")
        return role

    def change_role(self, actor: Actor, user_id: int, role_name: str) -> User:
        role = self._role(role_name)
        target, active_admins = self._locked_target(user_id)
        check_role_change(actor, target, role, active_admins)
        if target.role_id != role.id:
            self.audit.record(
                actor.id,
                AuditAction.user_role_change,
                AuditEntity.user,
                target.id,
                {"role": {"before": target.role_name, "after": role.name}},
            )
            target.role = role
        self.db.commit()  # also releases the locks on a no-op
        self.db.refresh(target)
        return target

    def set_role_by_operator(self, email: str, role_name: str) -> User:
        """Operator path (CLI/seeder) to bootstrap the first admin, with shell access as the only
        authorization. Audited with no actor. Still refuses to remove the last active admin."""
        role = self._role(role_name)
        active_admins = len(self.repository.lock_active_admin_ids())
        target = self.repository.get_by_email_for_update(email)
        if target is None:
            raise NotFoundError("User not found")
        if role.name != UserRole.admin and is_last_active_admin(target, active_admins):
            raise ConflictError("Cannot remove the last active admin")
        if target.role_id != role.id:
            self.audit.record(
                None,
                AuditAction.user_role_change,
                AuditEntity.user,
                target.id,
                {"role": {"before": target.role_name, "after": role.name}, "via": "operator"},
            )
            target.role = role
        self.db.commit()
        self.db.refresh(target)
        return target

    def set_active(self, actor: Actor, user_id: int, is_active: bool) -> User:
        target, active_admins = self._locked_target(user_id)
        check_active_change(actor, target, is_active, active_admins)
        if target.is_active != is_active:
            self.audit.record(
                actor.id,
                AuditAction.user_activate if is_active else AuditAction.user_deactivate,
                AuditEntity.user,
                target.id,
                {"is_active": {"before": target.is_active, "after": is_active}},
            )
            target.is_active = is_active
        self.db.commit()
        self.db.refresh(target)
        return target
