from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.users.models import User
from aptum.modules.users.schemas import CurrentUserRead
from aptum.modules.users.service import UserService

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


@router.post("/me/sessions/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_my_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """Sign the caller out everywhere. Takes effect on ID tokens when FIREBASE_CHECK_REVOKED is on; otherwise once they expire (1 h)."""
    UserService(db).revoke_sessions(current_user)
