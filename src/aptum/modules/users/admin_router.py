from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from aptum.common.pagination import Page, PageParams, page_params
from aptum.core.dependencies import get_db
from aptum.core.permissions import Permission, require
from aptum.modules.users.admin_service import UserAdminService
from aptum.modules.users.models import User
from aptum.modules.users.schemas import ActiveUpdate, AdminUserRead, RoleUpdate

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get(
    "",
    response_model=Page[AdminUserRead],
    dependencies=[Depends(require(Permission.user_list_read))],
)
def list_users(
    role: Annotated[str | None, Query(min_length=1, max_length=32, description="Role name")] = None,
    is_active: bool | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=255, description="Email contains")] = None,
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    """Users by id. Needs `user:list_read`.

    401 bad token; 403 missing permission; 422 invalid filter."""
    items, total = UserAdminService(db).list_page(page, role=role, is_active=is_active, email_query=q)
    return {"items": items, "total": total}


@router.patch("/{user_id}/role", response_model=AdminUserRead)
def change_role(
    user_id: int,
    data: RoleUpdate,
    current_user: User = Depends(require(Permission.user_manage_roles)),
    db: Session = Depends(get_db),
):
    """Set the user's role, by name. Needs `user:manage_roles`. Audited.

    401 bad token; 403 missing permission, acting on an admin without being one, or on a user or
    role holding permissions you lack; 404 unknown user or role; 409 your own account, or it
    would leave no active admin."""
    return UserAdminService(db).change_role(current_user, user_id, data.role)


@router.patch("/{user_id}/active", response_model=AdminUserRead)
def set_active(
    user_id: int,
    data: ActiveUpdate,
    current_user: User = Depends(require(Permission.user_deactivate)),
    db: Session = Depends(get_db),
):
    """Activate or deactivate the user; inactive users get 403 on every request. Needs
    `user:deactivate`. Audited.

    401 bad token; 403 missing permission, acting on an admin without being one, or on a user
    holding permissions you lack; 404 unknown user; 409 your own account, or it would leave no
    active admin."""
    return UserAdminService(db).set_active(current_user, user_id, data.is_active)
