from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AptumError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str) -> None:
        self.detail = detail


class NotFoundError(AptumError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AptumError):
    status_code = status.HTTP_409_CONFLICT


async def _aptum_error_handler(request: Request, exc: AptumError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AptumError, _aptum_error_handler)
