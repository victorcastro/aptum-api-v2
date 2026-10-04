from datetime import datetime

from pydantic import BaseModel, ConfigDict

from aptum.common.enums import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # Plain str: Firebase already verified it, and re-validating on output turns any address
    # email-validator dislikes (reserved domains like .test) into a 500 for that user.
    email: str
    is_active: bool
    role: UserRole


class CurrentUserRead(UserRead):
    # What the caller may do, for the UI to show or hide actions. The server checks every write.
    permissions: list[str]


class AdminUserRead(UserRead):
    created_at: datetime


class RoleUpdate(BaseModel):
    role: UserRole


class ActiveUpdate(BaseModel):
    is_active: bool
