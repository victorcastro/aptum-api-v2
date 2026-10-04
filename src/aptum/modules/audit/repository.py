from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aptum.modules.audit.models import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, entry: AuditLog) -> None:
        """No commit: the entry is written in the same transaction as the change it records."""
        self.db.add(entry)

    def list_page(
        self,
        *,
        entity_type: str | None,
        entity_id: int | None,
        actor_user_id: int | None,
        action: str | None,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        if entity_type is not None:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.where(AuditLog.entity_id == entity_id)
        if actor_user_id is not None:
            query = query.where(AuditLog.actor_user_id == actor_user_id)
        if action is not None:
            query = query.where(AuditLog.action == action)
        if since is not None:
            query = query.where(AuditLog.created_at >= since)
        if until is not None:
            query = query.where(AuditLog.created_at < until)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all()
        return list(items), total
