"""Bring the permissions and system roles in the database in line with the code. Runs on every
container start, right after the migrations (see Dockerfile); safe to run any number of times.

    uv run python -m aptum.modules.roles.sync

- Permissions: `core.permissions.Permission` is the source. Missing codes are added, descriptions
  updated, codes no longer in the enum deleted (and so taken from every role).
- System roles (`user`, `moderator`, `admin`): created when missing, with
  `DEFAULT_ROLE_PERMISSIONS`. An existing one keeps whatever permissions an admin gave it.
- `admin` always ends up holding every permission.

Role changes are audited with no actor and `"via": "sync"`, only when something changed. One
transaction: if anything fails nothing is written, and the container does not start.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity, UserRole
from aptum.core.config import get_settings
from aptum.core.logging_config import configure_logging
from aptum.core.permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSION_DESCRIPTIONS,
    Permission,
)
from aptum.db.session import SessionLocal
from aptum.modules.audit.service import AuditService
from aptum.modules.roles.repository import RoleRepository
from aptum.modules.roles.service import permission_changes

logger = logging.getLogger(__name__)

_LOCK_KEY = 0x41505455_524F4C45  # "APTU" "ROLE": any fixed bigint, unique to this job

SYSTEM_ROLE_DESCRIPTIONS: dict[UserRole, str] = {
    UserRole.user: "Every new user: manages their own CV",
    UserRole.moderator: "Keeps the shared catalogs clean",
    UserRole.admin: "Every permission, always",
}


@dataclass(frozen=True)
class PermissionPlan:
    create: dict[str, str]
    update: dict[str, str]
    delete: list[str]

    def __bool__(self) -> bool:
        return bool(self.create or self.update or self.delete)


def plan_permissions(stored: Mapping[str, str], wanted: Mapping[str, str]) -> PermissionPlan:
    """What turns `stored` into `wanted` (both code -> description)."""
    return PermissionPlan(
        create={code: wanted[code] for code in wanted if code not in stored},
        update={code: wanted[code] for code in wanted if code in stored and stored[code] != wanted[code]},
        delete=sorted(code for code in stored if code not in wanted),
    )


def wanted_permissions() -> dict[str, str]:
    return {permission.value: PERMISSION_DESCRIPTIONS[permission] for permission in Permission}


def sync(db: Session) -> list[str]:
    """Apply and commit. Returns one line per change (empty when already in sync)."""
    # Two containers starting at once take turns instead of racing on the unique codes.
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _LOCK_KEY})
    repository = RoleRepository(db)
    audit = AuditService(db)
    report: list[str] = []

    stored = {permission.code: permission for permission in repository.list_permissions()}
    roles = {role.name: role for role in repository.list_roles()}
    before = {name: role.permission_codes for name, role in roles.items()}

    plan = plan_permissions({code: row.description for code, row in stored.items()}, wanted_permissions())
    for code in plan.delete:
        permission = stored.pop(code)
        for role in roles.values():
            if permission in role.permissions:
                role.permissions.remove(permission)
        repository.delete_permission(permission)
        report.append(f"permission deleted: {code}")
    for code, description in plan.create.items():
        stored[code] = repository.create_permission(code, description)
        report.append(f"permission created: {code}")
    for code, description in plan.update.items():
        stored[code].description = description
        report.append(f"permission description updated: {code}")

    for name in UserRole:
        role = roles.get(name)
        if role is None:
            codes = sorted(DEFAULT_ROLE_PERMISSIONS[name])
            role = repository.create(
                name, SYSTEM_ROLE_DESCRIPTIONS[name], [stored[code] for code in codes], is_system=True
            )
            roles[name] = role
            audit.record(
                None,
                AuditAction.role_create,
                AuditEntity.role,
                role.id,
                {"name": role.name, "permissions": codes, "via": "sync"},
            )
            report.append(f"role created: {name}")
        elif not role.is_system:  # a custom role took a system name before it existed
            raise RuntimeError(f"Role {name!r} exists but is not a system role; rename it and run sync again")

    admin = roles[UserRole.admin]
    admin.permissions = [stored[code] for code in sorted(stored)]

    db.flush()
    for name, codes in before.items():
        if name not in roles:
            continue
        changes = permission_changes(codes, roles[name].permission_codes)
        if changes:
            audit.record(
                None,
                AuditAction.role_update,
                AuditEntity.role,
                roles[name].id,
                {"permissions": changes, "via": "sync"},
            )
            report.append(f"role {name}: {changes}")

    db.commit()
    return report


def main() -> None:
    configure_logging(get_settings().log_level)
    with SessionLocal() as db:
        report = sync(db)
    for line in report:
        logger.info("roles sync: %s", line)
    logger.info("roles sync: %s", f"{len(report)} change(s)" if report else "already in sync")


if __name__ == "__main__":
    main()
