from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from aptum.core.config import get_settings
from aptum.core.exceptions import register_exception_handlers
from aptum.core.logging_config import configure_logging
from aptum.modules.companies.router import router as companies_router
from aptum.modules.cv.router import router as cv_router
from aptum.modules.matching.router import router as matching_router
from aptum.modules.profile.router import router as profile_router
from aptum.modules.users.router import router as users_router



@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(get_settings().log_level)
    yield


docs_enabled = get_settings().environment != "production"

app = FastAPI(
    title="Aptum API",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

register_exception_handlers(app)

app.include_router(users_router)
app.include_router(profile_router)
app.include_router(companies_router)
app.include_router(cv_router)
app.include_router(matching_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if docs_enabled:

    @app.get("/docs", include_in_schema=False)
    def scalar_docs():
        return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)
