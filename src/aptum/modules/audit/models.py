from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aptum.db.base import Base


class AuditLog(Base):
    """Append-only record of privileged changes. `entity_id` has no foreign key on purpose: the
    entry outlives the entity (merged or deleted companies)."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, default=None
    )
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[int] = mapped_column(BigInteger)
    # {"field": {"before": x, "after": y}} for changed fields only, plus action-specific context.
    changes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
