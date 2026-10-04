from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_db
from aptum.core.permissions import Permission, require
from aptum.modules.roles.schemas import PermissionRead, RoleCreate, RoleRead, RoleUpdate
from aptum.modules.roles.service import RoleService
from aptum.modules.users.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/permissions",
    response_model=list[PermissionRead],
    dependencies=[Depends(require(Permission.role_read))],
)
def list_permissions(db: Session = Depends(get_db)):
    """Every permission a role can hold, by code. Needs `role:read`.

    401 bad token; 403 missing permission."""
    return RoleService(db).list_permissions()


@router.get(
    "/roles",
    response_model=list[RoleRead],
    dependencies=[Depends(require(Permission.role_read))],
)
def list_roles(db: Session = Depends(get_db)):
    """Roles by name, with their permissions and how many users hold each. Needs `role:read`.

    401 bad token; 403 missing permission."""
    return RoleService(db).list_roles()


@router.post("/roles", response_model=RoleRead, status_code=201)
def create_role(
    data: RoleCreate,
    current_user: User = Depends(require(Permission.role_manage)),
    db: Session = Depends(get_db),
):
    """Create a custom role. Needs `role:manage`, and you must hold every permission you grant.
    Audited.

    401 bad token; 403 missing permission or granting one you lack; 409 name taken;
    422 invalid name or unknown permission code."""
    return RoleService(db).create(current_user, data)


@router.patch("/roles/{role_id}", response_model=RoleRead)
def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(require(Permission.role_manage)),
    db: Session = Depends(get_db),
):
    """Partial edit; `permissions` replaces the whole set. Needs `role:manage`, and you must hold
    every permission the role has before and after. System roles (`user`, `moderator`): only an
    admin edits them, and they keep their name. Audited.

    401 bad token; 403 missing permission, system role without being admin, or a permission you
    lack; 404 unknown role; 409 the admin role, renaming a system role, or name taken;
    422 invalid name or unknown permission code."""
    return RoleService(db).update(current_user, role_id, data)


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    current_user: User = Depends(require(Permission.role_manage)),
    db: Session = Depends(get_db),
):
    """Delete a custom role nobody holds. Needs `role:manage`, and you must hold every
    permission it has. Audited.

    401 bad token; 403 missing permission or a permission you lack; 404 unknown role;
    409 system role or still assigned to users."""
    RoleService(db).delete(current_user, role_id)
    return Response(status_code=204)
