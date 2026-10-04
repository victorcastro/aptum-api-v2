from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, validate_by_name=True, validate_by_alias=True)

    id: int
    # Plain str: Firebase already verified it, and re-validating on output turns any address
    # email-validator dislikes (reserved domains like .test) into a 500 for that user.
    email: str
    is_active: bool
    # The role's name (read from `User.role_name`): system or custom, so a plain string.
    role: str = Field(validation_alias="role_name")


class CurrentUserRead(UserRead):
    # What the caller may do, for the UI to show or hide actions. The server checks every write.
    permissions: list[str]


class AdminUserRead(UserRead):
    created_at: datetime


class RoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=32, description="Role name")


class ActiveUpdate(BaseModel):
    is_active: bool
