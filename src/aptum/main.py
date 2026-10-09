from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from scalar_fastapi import get_scalar_api_reference

from aptum.core.config import get_settings
from aptum.core.dependencies import get_current_user
from aptum.core.exceptions import register_exception_handlers
from aptum.core.logging_config import configure_logging
from aptum.modules.audit.router import router as audit_router
from aptum.modules.commons.router import router as commons_router
from aptum.modules.companies.router import router as companies_router
from aptum.modules.cv.router import router as cv_router
from aptum.modules.matching.router import router as matching_router
from aptum.modules.profile.router import router as profile_router
from aptum.modules.roles.router import router as roles_router
from aptum.modules.skill_categories.router import router as skill_categories_router
from aptum.modules.skills.router import router as skills_router
from aptum.modules.users.admin_router import router as admin_users_router
from aptum.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(get_settings().log_level)
    yield


docs_enabled = get_settings().environment != "production"

app = FastAPI(
    title="Aptum API",
    version=version("aptum-api"),  # single source of truth: pyproject.toml
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

register_exception_handlers(app)

cors_origins = get_settings().cors_origin_list
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

app.include_router(users_router)
app.include_router(profile_router)
app.include_router(commons_router)
app.include_router(companies_router)
app.include_router(skills_router)
app.include_router(skill_categories_router)
app.include_router(cv_router)
app.include_router(matching_router)
app.include_router(admin_users_router)
app.include_router(roles_router)
app.include_router(audit_router)


class HealthRead(BaseModel):
    status: str


@app.get("/health")
def health() -> HealthRead:
    return HealthRead(status="ok")


class VersionRead(BaseModel):
    version: str


@app.get("/version", dependencies=[Depends(get_current_user)])
def api_version() -> VersionRead:
    return VersionRead(version=app.version)


if docs_enabled:

    @app.get("/docs", include_in_schema=False)
    def scalar_docs():
        return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)
