from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.common.pagination import Page, PageParams, page_params
from aptum.core.dependencies import get_db
from aptum.core.permissions import Permission, require
from aptum.modules.audit.schemas import AuditLogRead
from aptum.modules.audit.service import AuditService

router = APIRouter(prefix="/admin/audit-logs", tags=["admin"])


@router.get(
    "",
    response_model=Page[AuditLogRead],
    dependencies=[Depends(require(Permission.audit_read))],
)
def list_audit_logs(
    entity_type: AuditEntity | None = None,
    entity_id: int | None = None,
    actor_user_id: int | None = None,
    action: AuditAction | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    """Privileged changes, newest first. Needs `audit:read`.

    401 bad token; 403 missing permission; 422 invalid filter."""
    items, total = AuditService(db).list(
        page,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        action=action,
        since=since,
        until=until,
    )
    return {"items": items, "total": total}
