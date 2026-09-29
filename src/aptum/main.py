from fastapi import FastAPI

from aptum.core.exceptions import register_exception_handlers
from aptum.modules.companies.router import router as companies_router
from aptum.modules.cv.router import router as cv_router
from aptum.modules.matching.router import router as matching_router
from aptum.modules.profile.router import router as profile_router
from aptum.modules.users.router import router as users_router

app = FastAPI(title="Aptum Agent")

register_exception_handlers(app)

app.include_router(users_router)
app.include_router(profile_router)
app.include_router(companies_router)
app.include_router(cv_router)
app.include_router(matching_router)


@app.get("/health")
def health():
    return {"status": "ok"}
