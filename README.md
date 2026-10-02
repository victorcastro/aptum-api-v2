# Aptum API

Backend for Aptum: CV data, PDF generation and matching.

**Stack:** Python 3.12, uv, FastAPI, SQLAlchemy 2.0, Alembic, Postgres + pgvector.

## Local development

Requires [uv](https://docs.astral.sh/uv/) and a Postgres with the `vector` extension.

```bash
cp .env.example .env            # then fill in the values
uv sync
uv run alembic upgrade head
uv run fastapi dev src/aptum/main.py
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs (disabled when `ENVIRONMENT=production`)
- Health: http://localhost:8000/health

Useful commands:

```bash
uv run ruff check src                                   # lint
uv run alembic revision --autogenerate -m "<message>"   # new migration
uv run alembic check                                    # models match migrations
```

## Docker

The image applies pending migrations on startup and then serves the API on port 8000.

```bash
docker build -t aptum-api .
docker run --rm -p 8000:8000 --env-file .env aptum-api
```
