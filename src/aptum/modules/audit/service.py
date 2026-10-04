from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.common.pagination import PageParams
from aptum.modules.audit.models import AuditLog
from aptum.modules.audit.repository import AuditRepository

# Never stored, whatever a caller passes. Matched as substrings of the key.
_SECRET_MARKERS = ("password", "secret", "token", "firebase_uid", "private_key", "api_key")


def snapshot(entity: object, fields: Iterable[str]) -> dict[str, Any]:
    return {field: getattr(entity, field) for field in fields}


def diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Changed fields only: {"field": {"before": old, "after": new}}."""
    return {
        field: {"before": before.get(field), "after": value}
        for field, value in after.items()
        if before.get(field) != value
    }


def redact(changes: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: redact(value) if isinstance(value, Mapping) else value
        for key, value in changes.items()
        if not any(marker in key.lower() for marker in _SECRET_MARKERS)
    }


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repository = AuditRepository(db)

    def record(
        self,
        actor_user_id: int | None,
        action: AuditAction,
        entity_type: AuditEntity,
        entity_id: int,
        changes: Mapping[str, Any],
    ) -> AuditLog:
        """Stage an entry in the caller's transaction; it is committed (or rolled back) with the change."""
        entry = AuditLog(
            actor_user_id=actor_user_id,
            action=action.value,
            entity_type=entity_type.value,
            entity_id=entity_id,
            changes=redact(changes),
        )
        self.repository.add(entry)
        return entry

    def list(
        self,
        page: PageParams,
        *,
        entity_type: AuditEntity | None = None,
        entity_id: int | None = None,
        actor_user_id: int | None = None,
        action: AuditAction | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> tuple[list[AuditLog], int]:
        return self.repository.list(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            action=action,
            since=since,
            until=until,
            limit=page.limit,
            offset=page.offset,
        )
