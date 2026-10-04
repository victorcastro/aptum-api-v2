from collections.abc import Iterable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.core.exceptions import ConflictError, NotFoundError
from aptum.core.permissions import Actor
from aptum.modules.audit.service import AuditService, diff, snapshot
from aptum.modules.roles.models import PermissionRecord, Role
from aptum.modules.roles.policy import check_delete_role, check_edit_role, check_grant
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.roles.schemas import RoleCreate, RoleRead, RoleUpdate


def permission_changes(before: Iterable[str], after: Iterable[str]) -> dict[str, list[str]]:
    """{"added": [...], "removed": [...]}, sorted; empty when nothing changed."""
    before, after = set(before), set(after)
    changes = {"added": sorted(after - before), "removed": sorted(before - after)}
    return {key: codes for key, codes in changes.items() if codes}


class RoleService:
    """Custom roles and the permissions of system roles. Every write is checked by
    roles/policy.py and audited in the same transaction."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = RoleRepository(db)
        self.audit = AuditService(db)

    def list_permissions(self) -> list[PermissionRecord]:
        return self.repository.list_permissions()

    def list_roles(self) -> list[RoleRead]:
        counts = self.repository.user_counts()
        return [self._read(role, counts.get(role.id, 0)) for role in self.repository.list_roles()]

    def create(self, actor: Actor, data: RoleCreate) -> RoleRead:
        codes = {permission.value for permission in data.permissions}
        check_grant(actor, codes)
        try:
            role = self.repository.create(data.name, data.description, self.repository.get_permissions(codes))
        except IntegrityError as exc:
            raise ConflictError("A role with that name already exists") from exc
        self.audit.record(
            actor.id,
            AuditAction.role_create,
            AuditEntity.role,
            role.id,
            {"name": role.name, "description": role.description, "permissions": sorted(codes)},
        )
        self.db.commit()
        return self._read(role, 0)

    def update(self, actor: Actor, role_id: int, data: RoleUpdate) -> RoleRead:
        role = self._get_for_update(role_id)
        before_codes = role.permission_codes
        after_codes = before_codes if data.permissions is None else {p.value for p in data.permissions}
        renaming = data.name is not None and data.name != role.name
        check_edit_role(actor, role, after_codes, renaming=renaming)

        # Query before changing the role: autoflush would otherwise send a clashing name here,
        # outside the IntegrityError handling below.
        new_permissions = self.repository.get_permissions(after_codes) if after_codes != before_codes else None
        before = snapshot(role, ("name", "description"))
        if renaming:
            role.name = data.name
        if data.description is not None:
            role.description = data.description
        changes: dict[str, Any] = diff(before, snapshot(role, ("name", "description")))
        if new_permissions is not None:
            role.permissions = new_permissions
            changes["permissions"] = permission_changes(before_codes, after_codes)

        if changes:
            self.audit.record(actor.id, AuditAction.role_update, AuditEntity.role, role.id, changes)
        try:
            self.db.commit()  # also releases the lock on a no-op
        except IntegrityError as exc:  # renamed to a name taken meanwhile
            raise ConflictError("A role with that name already exists") from exc
        self.db.refresh(role)
        return self._read(role, self.repository.count_users(role.id))

    def delete(self, actor: Actor, role_id: int) -> None:
        role = self._get_for_update(role_id)
        check_delete_role(actor, role, self.repository.count_users(role.id))
        self.audit.record(
            actor.id,
            AuditAction.role_delete,
            AuditEntity.role,
            role.id,
            {"name": role.name, "description": role.description, "permissions": sorted(role.permission_codes)},
        )
        self.repository.delete(role)
        try:
            self.db.commit()
        except IntegrityError as exc:  # assigned to someone meanwhile (FK RESTRICT)
            raise ConflictError("Role is assigned to users; give them another role first") from exc

    def _get_for_update(self, role_id: int) -> Role:
        role = self.repository.get_for_update(role_id)
        if role is None:
            raise NotFoundError("Role not found")
        return role

    @staticmethod
    def _read(role: Role, users_count: int) -> RoleRead:
        return RoleRead(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=sorted(role.permission_codes),
            users_count=users_count,
        )
