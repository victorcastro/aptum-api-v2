from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from aptum.core.permissions import Permission

# Lowercase identifier, like the system roles: it shows up in filters, logs and the CLI.
RoleName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")]
Description = Annotated[str, Field(max_length=255)]


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str


class RoleRead(BaseModel):
    id: int
    name: str
    description: str
    is_system: bool
    permissions: list[str]
    users_count: int


class RoleCreate(BaseModel):
    name: RoleName
    description: Description = ""
    # Validated against the enum, which roles.sync mirrors into the table: unknown codes are 422.
    permissions: list[Permission] = []


class RoleUpdate(BaseModel):
    """Partial update: only the fields sent are changed. `permissions` replaces the whole set."""

    name: RoleName | None = None
    description: Description | None = None
    permissions: list[Permission] | None = None
