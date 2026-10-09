# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Codex, Cursor, etc.) when working with code in this repository.

## Language

Respond in English by default. Only respond in Spanish when I explicitly ask for it in that specific message.

## Stack

Python 3.12 + uv, FastAPI, SQLAlchemy 2.0 (typed `Mapped`, sync `Session`), Alembic, Postgres (psycopg3) + pgvector.

## Branches

Always work on a branch named after the release version: `version/<x.y.z>` (e.g. `version/1.8.0`), created from `staging`. The branch version must match `version` in `pyproject.toml` and the top `CHANGELOG.md` entry.

## Commands

- Run API: `uv run fastapi dev src/aptum/main.py`
- Apply migrations: `uv run alembic upgrade head`, then `uv run python -m aptum.modules.roles.sync` (permissions and system roles; the container runs both on start)
- New migration after model changes: `uv run alembic revision --autogenerate -m "<message>"`, then review it (autogenerate does not create/drop extensions or native enum types).
- Check models match migrations: `uv run alembic check`
- Config comes from `.env` (see `.env.example`); `DATABASE_URL` in the environment overrides it.
- Run tests: `uv run pytest` (synthetic data only, no database needed). The migration round-trip test runs only with `MIGRATION_TEST_DATABASE_URL` pointing at a throwaway Postgres (see `tests/test_migrations.py`).
- No Docker/Postgres is provided for development: bring your own Postgres with the `vector` extension.

## Layout

One folder per feature under `src/aptum/modules/<x>/` with `models.py`, `repository.py`, `service.py`, `router.py`, `schemas.py`. The ORM model doubles as the entity. Repositories never commit (they may `flush` for ids or early unique errors); the service commits once per operation and turns `IntegrityError` on unique names into 409 (or, in get-or-create, returns the row created meanwhile). Explicit `rollback()` only when the session is used again afterwards; otherwise `get_db` closing the session rolls back. Shared code lives in `core/` (config, security, dependencies, exceptions), `common/` (enums, constants, types, utils) and `db/` (`Base`, `TimestampMixin`, constraint helpers, migrations).

## CV data model

- Ownership chain: `users` → `profiles` (1–1, created at registration) → CV tables (`experiences`, `educations`, `profile_languages`, `profile_skills`, `profile_links`, `certifications`, `projects`) → `experience_functions` / `experience_skills`. All `ON DELETE CASCADE`.
- `companies`, `industries` and `skills` are shared catalogs with no owner. `created_by_user_id` is `SET NULL` on user delete.
- Services always take the authenticated `user_id`, resolve that user's profile and filter by `profile_id`. Never accept `profile_id`/`user_id` from the client. Rows that belong to someone else return 404.
- CV dates are month/year only: the API speaks `YYYY-MM` (`common/types.YearMonth`), the DB stores the first day of the month and enforces it with a CHECK.
- Authorization: routers depend on `core/permissions.require(Permission.x)`, never on role names. The `Permission` enum is the source of permissions; roles and their grants live in tables (`modules/roles`), kept in line with the enum by `roles.sync` (run on every container start; `admin` always holds every permission). `DEFAULT_ROLE_PERMISSIONS` is only for creating missing system roles. Writes on roles follow anti-escalation: never grant, assign or remove permissions the actor lacks. Data-dependent rules are pure functions in `modules/<x>/policy.py` (e.g. `can_edit_company`), unit-tested without a DB. Privileged writes call `AuditService.record` before the commit so the entry shares the transaction; never put secrets in `changes`.
- Hiring through a consultancy: `experiences.employer_id` is who hires (NTT Data), `experiences.client_id` is where the work happens (Banco BCP). The client's industry is the relevant one for matching.

<!-- engly:start v1.5.0 -->
@.engly/engly.md
<!-- engly:end -->
