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
uv run ruff check src tests                             # lint
uv run pytest                                           # tests (synthetic data, no DB)
uv run alembic revision --autogenerate -m "<message>"   # new migration
uv run alembic check                                    # models match migrations
```

## Roles and permissions

Every user has one role. Routers ask for a permission, never a role
(`require(Permission.x)` in `src/aptum/core/permissions.py`). Roles and what they grant live in
the database (`roles`, `permissions`, `role_permissions`), so admins can create roles and change
grants from `/admin/roles` without a deploy.

System roles always exist and are never deleted or renamed:

| Role | Default permissions | Editable |
|---|---|---|
| `user` | none (manages their own CV) | by an admin |
| `moderator` | `company:update_any`, `company:delete`, `skill:update_any`, `industry:manage`, `user:list_read`, `role:read` | by an admin |
| `admin` | every permission, always | never |

Custom roles are created, edited and deleted with `role:manage`. Nobody grants, assigns, edits
or deletes a role holding permissions they lack. A role still assigned to users cannot be
deleted.

Permissions are born in code: the `Permission` enum is the source, and each one only guards
something once an endpoint asks for it. On every start, after the migrations, the container runs
`python -m aptum.modules.roles.sync`. It copies the enum into `permissions`, recreates missing
system roles and gives `admin` every permission. Run it by hand after `alembic upgrade head`
when working locally.

To add a permission:

1. Add it to `Permission` and `PERMISSION_DESCRIPTIONS` in `core/permissions.py`.
2. Guard the endpoint with `require(Permission.new_one)`.
3. Deploy. The sync inserts it and gives it to `admin`; grant it to other roles with
   `PATCH /admin/roles/{id}`.

Create the first admin (the user must have logged in once), then manage roles from `/admin/users`:

```bash
uv run python -m aptum.modules.users.cli set-role --email you@example.com --role admin
```

New users always get the `user` role.

Locally, `uv run python -m aptum.db.seed_demo [--reset]` creates one test user per role, linked to
their Firebase accounts, with data to try each role (see the module docstring):

| Email | Role | Data |
|---|---|---|
| `user@aptum.test` | user | Full demo CV; created "Acme Startup" (editable) and "BCP" (in use) |
| `moderator@aptum.test` | moderator | Catalog to fix: skills "Pyhton", "ReactJS", industry "Bankng" |
| `admin@aptum.test` | admin | "BCP" to merge into "Banco de Credito del Peru"; `candidate@` and `inactive@` to manage; custom role `catalog_editor` |

Every privileged change (company edit/merge/delete, skill and industry changes, user role and
active changes, role create/edit/delete) is written to `audit_logs` in the same transaction, readable through
`GET /admin/audit-logs`.

## Docker

The image applies pending migrations and the roles sync on startup, then serves the API on port 8000.

```bash
docker build -t aptum-api .
docker run --rm -p 8000:8000 --env-file .env aptum-api
```

## ATS CV generation (release 1.1.0)

The ATS CV is the default for every user; there is no switch.

### What it does

- `GET /cv/export` (no `template` query parameter) renders the ATS PDF: one column, Helvetica,
  no tables/images/icons/lines, standard headings (Summary, Experience, Skills, Education,
  Certifications, Projects, Languages), `Mon YYYY - Mon YYYY` dates, at most 2 pages. The saved
  template preference no longer applies to it; an explicit `?template=software-engineer`
  still renders that legacy layout.
- `POST /cv/ats/export` with `{"job_description": "..."}` (optional) renders the ATS PDF tailored to
  the offer: offer-relevant skills first (max 25), only skills from the profile.
- `POST /cv/ats/report` with the same body returns the JSON report of that same CV:
  `page_count`, `years_of_experience`, `skills`, `warnings`, `fidelity_issues`, `keyword_coverage`.
  Warnings are never printed in the PDF.
- Skills are printed one line per category: `LLMs & AI`, `Backend`, `Cloud & DevOps`,
  `Architecture`, `Mobile`, `Other`. Up to 25, ordered by evidence (no manual order): mentioned
  by the offer, then used in the most recent experience, then `level` / `years_experience`,
  then alphabetical. Profile skills no longer have a `position` field.
- Years of experience are computed from experience dates (overlaps merged, per `area` too); a
  summary claiming more years than the dates support is corrected to the computed figure.
- Roles that ended more than 7 years ago are shortened to 2 bullets; near-duplicate bullets and
  filler-only bullets are removed; bullets without a number are reported as `missing_metric`.
- Fidelity check: employers, titles, dates and numbers in the CV must exist in the profile.

Deterministic configuration (no LLM involved), easy to extend:

- Skill → category dictionary: `src/aptum/modules/skills/data/skill_dictionary.json` (bump `version`).
- Filler phrases: `src/aptum/modules/cv/ats/filler_phrases.txt`.

### New API fields (always accepted, optional)

| Endpoint | Field | Values |
| --- | --- | --- |
| `PATCH /profile/me` | `linkedin_url`, `github_url`, `portfolio_url` | http(s) URL; LinkedIn/GitHub must be on their domain |
| `PATCH /profile/me` | `work_authorization` | `authorized`, `requires_sponsorship` |
| `PATCH /profile/me` | `work_authorization_country` | ISO 3166-1 alpha-2 (e.g. `CA`) |
| `PATCH /profile/me` | `open_to_relocation` | boolean (default `false`, not nullable) |
| `POST/PATCH /profile/me/experiences` | `area` | `backend`, `mobile`, `ai`, `other` |
| `POST/PATCH /profile/me/educations` | `start_year`, `end_year` | 1900-2100, end >= start |
| `POST/PATCH /profile/me/skills` | `category` | one of the six categories; omitted = dictionary |
| `POST/PATCH /profile/me/languages` | `language_code`, `proficiency` | codes from `GET /commons/languages` and `GET /commons/language-levels` (`A1`-`C2`, `Native`) |

All of them are returned by the matching `GET` endpoints (`GET /profile/me` included).
