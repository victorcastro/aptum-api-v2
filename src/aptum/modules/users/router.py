from fastapi import APIRouter, Depends

from aptum.core.dependencies import get_current_user
from aptum.modules.users.models import User
from aptum.modules.users.schemas import CurrentUserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> CurrentUserRead:
    """The caller with role and permissions. 401 bad token; 403 email not verified or inactive user."""
    return CurrentUserRead(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        role=current_user.role_name,
        permissions=sorted(current_user.permissions),
    )
