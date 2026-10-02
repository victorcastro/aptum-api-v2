# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN useradd --system --uid 1001 --no-create-home aptum

# The project is installed in editable mode, so the venv points at /app/src:
# both must land at the same path as in the build stage.
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/src ./src
COPY alembic.ini ./

USER aptum
EXPOSE 8000

# Migrations run on startup; if they fail, the API must not start.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn aptum.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
