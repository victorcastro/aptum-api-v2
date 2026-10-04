from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from aptum.common.enums import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
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
