from fastapi import APIRouter, Depends

from aptum.core.dependencies import get_current_user
from aptum.modules.users.models import User
from aptum.modules.users.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
