# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/).

## [1.6.0] - 2026-10-08

### Added

- `projects.show_url` (default `true`), exposed as `show_url` on the project create/update/read
  schemas. When `true` and the project has a `url`, the link is printed under the project in every
  template (a real hyperlink in `software-engineer` and DOCX, plain text in `basic`). When `false` the
  `url` stays on the project but is not printed. Migration `0006`.

### Changed

- All CV templates (`basic`, `software-engineer` and the DOCX export) now show and hide the same
  profile data under the same conditions; each one only decides how it looks.
- `basic` (ATS) now prints the certification issuer and credential link (when `show_credential_url`),
  the project link (when `show_url`) and a `Technologies` line per role. The `Technologies` line is the
  last thing dropped when the 2-page limit forces trimming.
- `software-engineer` and DOCX now print education dates that only have years, include the region in the
  location line (like `basic`) and skip empty bullets.

## [1.5.0] - 2026-10-07

### Added

- `GET /cv/export?format=docx`: editable Word CV with the software-engineer layout. Uses named styles,
  a right tab stop for dates, real bullet lists and hyperlinks, so it stays editable in Word and
  Google Docs. `format` defaults to `pdf`; `template` is ignored for `docx`.

## [1.4.0] - 2026-10-05

### Added

- `certifications.show_credential_url` (default `true`), exposed as `show_credential_url` on the
  certification create/update/read schemas. When `false` the `credential_url` stays on the
  certification but is not printed on the CV. Migration `0005`.
- `profile_languages.is_active` (default `true`), exposed as `is_active` on the language create/update/read
  schemas. Inactive languages stay on the profile but are not printed on any CV template.

### Removed

- `description` on education (breaking): dropped from the model, the create/update/read schemas and
  every CV template. Existing education descriptions are deleted by migration `0005`.

## [1.3.3] - 2026-10-05

### Added

- `software-engineer` CV template: the certification's `credential_url` is printed after the issuer
  as a clickable link, when the certification has one.

### Changed

- `software-engineer` CV: the institution (education) and issuer (certification) now sit on their own line below the title, not bold.

## [1.3.2] - 2026-10-05

### Fixed

- CV preview/download failed with `AttributeError: 'ParaLines' object has no attribute 'ascent'` in the
  `software-engineer` template when an experience, education or certification title contained `&`
  (e.g. "R&D Engineer"). The date baseline now falls back to the title font size.

## [1.3.1] - 2026-10-05

### Added

- `GET /version`: returns `{"version"}` of the running backend. Requires a valid token; `/health` is unchanged.
- Experiences accept `skill_ids` (catalog skills used in the role) on `POST` and `PATCH /profile/me/experiences`, and return them as `skills`. On `PATCH`, sending `skill_ids` replaces the list and omitting it keeps it. An unknown skill is a 404. They print as "Technologies" in the CV.

### Fixed

- `software-engineer` CV template: the date range of each experience, education and certification
  now sits on the same line as its title, right-aligned, instead of on a line below. A long title
  wraps without moving or splitting the date, and the block never breaks across pages.

## [1.3.0] - 2026-10-04

Schema changes are in migration `0004_release_1_3_0`.

### Removed

- Breaking: the profile links feature. Endpoints `GET/POST /profile/me/links` and
  `PATCH/DELETE /profile/me/links/{link_id}`, the `profile_links` table and the `link_kind`
  enum. Existing rows are dropped, not migrated.
- Breaking: `linkedin_url`, `github_url` and `portfolio_url` on the profile. The migration
  copies them into `links`.

### Added

- `links` on the profile (`PATCH /profile`, `GET /profile`): the CV header links as one JSON
  list, in print order, `[{"kind", "label", "url", "visible"}]`. `kind` is `portfolio`,
  `linkedin`, `github` or `other`; `visible: false` hides the link on the CV without losing it.
  Up to 10 links, http(s) URLs, `linkedin`/`github` must match their host, one link per kind
  except `other`. The list is replaced as a whole on every update.
- `basic` CV template (the ATS layout) is now listed by `GET /cv/templates`, first, and can be
  saved as the default with `PATCH /cv/settings` or requested with `?template=basic`.

### Changed

- `GET /cv/export` without `?template=` now uses the user's saved template, and `basic` when none
  is saved (before, it always rendered the ATS layout and ignored the saved preference). Users
  who saved `software-engineer` through `PATCH /cv/settings` now get that layout by default.
- `GET /cv/settings` reports `basic` as the default template (was `software-engineer`).
- CV templates (software-engineer and ATS) print the visible `links` in the saved order.
- software-engineer template: header is now name, tagline, one line of contact data, and a line of
  full URLs (clickable). Smaller name and a navy accent on the
  name, links and section headings, softer gray for secondary text and rules. Still standard
  Helvetica, single column, no images or tables.

## [1.2.0] - 2026-10-04

Roles and permissions move from code to tables, so admins can create roles and choose what
each one grants without a deploy. Permissions themselves are still born in code: one only
guards something once an endpoint asks for it.

Schema changes are in migration `0003_release_1_2_0`.

### Added

- Tables `permissions`, `roles` (`is_system` for `user`, `moderator`, `admin`) and
  `role_permissions`. The migration seeds them with the grants that lived in code, so every
  user keeps exactly what they could do.
- `python -m aptum.modules.roles.sync`, run by the container on every start after the
  migrations: adds permissions new in code, updates descriptions, deletes the ones gone from
  code, recreates missing system roles, and keeps `admin` holding every permission.
  Idempotent, one transaction, serialized with an advisory lock; changes to roles are audited
  with `"via": "sync"`. If it fails, the API does not start.
- `GET /admin/permissions`, `GET /admin/roles` (`role:read`) and `POST/PATCH/DELETE
  /admin/roles` (`role:manage`), audited as `role.create`, `role.update` (permission diff as
  `added`/`removed`) and `role.delete`.
- Permissions `role:read` (moderator, admin) and `role:manage` (admin).
- Local seeder: a custom role `catalog_editor` to try the role endpoints.

### Changed

- `users.role` (string) becomes `users.role_id` (foreign key, `RESTRICT`). The API still
  speaks role names: `role` in user responses, `PATCH /admin/users/{id}/role` and the `role`
  filter of `GET /admin/users` accept any role name, system or custom. An unknown name returns
  404 (it was 422).
- Anti-escalation: nobody grants, assigns, edits or deletes a role holding permissions they
  lack, nor manages a user holding permissions they lack. Admin, holding them all, is never
  limited by it.
- The `admin` role cannot be edited or deleted. `user` and `moderator` can only be edited by an
  admin, and are never renamed or deleted. A role still assigned to users cannot be deleted.
- `set-role` CLI takes any role name in the table.
- `GET /companies` and `GET /skills`: `q` is optional. Without it they list the whole catalog in
  name order, paged by `limit` (1–100, default 100) and `offset`, for any signed-in user. With
  `q` the search is unchanged (top 20).
- The `software-engineer` CV template prints the work authorization line (for example `Requires
  visa sponsorship for Peru | Open to relocation`) inside Summary, in gray and left-aligned,
  as the default ATS CV already did. The country is optional: without it the line is generic.

## [1.1.0] - 2026-10-03

ATS-friendly CV generation for English-speaking markets. The ATS CV is the default for every
user (no feature flag).

All schema changes are in a single migration, `0002_release_1_1_0`.

### Added

- Skill categories: `profile_skills.category` with the values `LLMs & AI`, `Backend`,
  `Cloud & DevOps`, `Architecture`, `Mobile`, `Other`. The migration adds the column and
  backfills existing rows from a deterministic, versioned dictionary (`skills/data/skill_dictionary.json`, case-insensitive,
  with aliases; unknown skills go to `Other`).
- `GET /profile/me/skills/grouped`: the user's skills grouped by CV category, in the order the CV
  prints them (empty groups left out), sorted by name inside each group: `{"total", "groups":
  [{"category", "skills": [{"id", "skill_id", "name", "level", "years_experience"}]}]}`. `id` is
  the profile skill (used by `PATCH`/`DELETE`), `skill_id` the catalog skill.
  `GET /profile/me/skills` is unchanged.
- Language catalogs: tables `languages` (ISO 639-1 code, English name) and `language_levels`
  (CEFR `A1`-`C2` plus `Native`, ranked, with a short description), seeded by the migration and
  served by `GET /commons/languages` and `GET /commons/language-levels`. `profile_languages`
  references both by foreign key; codes outside the catalogs return 404 on
  `POST/PATCH /profile/me/languages`.
- `category` (optional) on `POST/PATCH /profile/me/skills` and in skill responses; when omitted
  it is classified with the same dictionary (`null` on PATCH re-classifies).
- New profile fields, all optional: `linkedin_url`, `github_url`, `portfolio_url` (validated
  URLs), `work_authorization` (`authorized`,
  `requires_sponsorship`), `work_authorization_country`, `open_to_relocation`; `area` on
  experiences (`backend`, `mobile`, `ai`, `other`); `start_year` / `end_year` on educations.
- ATS PDF: single column, standard font, no tables/images/icons/lines/photo, selectable text,
  standard headings (Summary, Experience, Skills, Education, Certifications, Projects,
  Languages), `Mon YYYY - Mon YYYY` dates, at most 2 pages. The header prints the profile
  links as visible URLs and one work authorization line only when set.
- Skills printed one line per category, up to 25, ordered by evidence: mentioned by the job
  offer first, then used in the most recent experience, then `level` and `years_experience`,
  then alphabetical. Only skills from the profile are ever printed.
- Generation rules: years of experience computed from experience dates (overlaps merged, total
  and per area) and locked in the LLM prompt; roles that ended more than 7 years ago shortened
  to 2 bullets; 2-page limit enforced by trimming the oldest, least relevant bullets (never a
  role); near-duplicate bullets and filler phrases (`cv/ats/filler_phrases.txt`) detected and
  removed or reported; bullets without a metric reported as warnings, never filled in.
- Fidelity check in code: employers, job titles, dates and numbers in the generated CV must
  exist in the profile; mismatches are repaired once and otherwise returned as
  `fidelity_issues`.
- Keyword coverage report for a job offer: keywords found, present in the CV, missing, and
  missing ones truthfully supported by the profile (suggested, not added).
- `POST /cv/ats/export` (ATS PDF, optional `job_description`) and `POST /cv/ats/report`
  (`page_count`, `years_of_experience`, `skills`, `warnings`, `fidelity_issues`,
  `keyword_coverage`).
- Duplicate education detection (same institution, overlapping titles) as a warning.
- Test suite (pytest, synthetic data only), run in CI.
- Role-based access control: `users.role` (`user` by default, `moderator`, `admin`) and
  permissions (`core/permissions.py`). `GET /users/me` adds `role` and `permissions`.
- `can_edit` on `/companies` responses (search, create, update), computed for the caller.
  `PATCH /companies/{id}`: moderators and admins edit any company; the creator only while no
  experience uses it (403 when in use, 404 for anyone else).
- Catalog moderation: `PATCH /skills/{id}` (rename), `POST /companies/industries`,
  `PATCH /companies/industries/{id}`, `POST /companies/{id}/merge` (admin) and
  `DELETE /companies/{id}` (unused companies only).
- User management: `GET /admin/users`, `PATCH /admin/users/{id}/role`,
  `PATCH /admin/users/{id}/active`. Nobody changes their own role or status, only admins
  manage admins, and the last active admin cannot be demoted or deactivated.
- Audit log (`audit_logs`) of privileged changes with before/after values, and
  `GET /admin/audit-logs`.
- Operator command `python -m aptum.modules.users.cli set-role` and seeder `--role`
  to create the first admin.

### Changed

- `GET /cv/export` without a `template` parameter now renders the ATS PDF for everyone, and the
  saved template preference (`/cv/settings`) no longer applies to it; `?template=` still renders
  the legacy templates.
- Experiences embed `CompanySummary` (same fields as before); `CompanyRead` from `/companies`
  adds `can_edit`.
- The matching prompt includes the computed years of experience as locked facts.
- The OpenAPI metadata now reports the package version (`1.1.0`), read from `pyproject.toml`.
- CV skill groups come from `profile_skills.category` (six standard groups)
  instead of the free-text catalog category (`skills.category`), in every template and in the
  same order as the ATS CV.
- Registration creates the user and their profile in one transaction.
- Repositories no longer commit; each service commits once per operation, so audit entries
  always share the transaction of the change they record.
- Creating a company or skill that someone else creates at the same moment returns the
  existing one instead of a 500; renaming a company to a name taken meanwhile returns 409.
- All CV templates render on A4 (the ATS PDF was US Letter), and every template prints the
  same Languages lines: language name and level code (`Spanish - Native`, `English - C1`).
- **Breaking:** `proficiency` on `/profile/me/languages` takes a level code from
  `GET /commons/language-levels` (`A1`-`C2`, `Native`) instead of `elementary`,
  `limited_working`, `professional_working`, `full_professional`, `native_or_bilingual`. The
  migration converts stored rows: elementary -> A2, limited_working -> B1,
  professional_working -> B2, full_professional -> C1, native_or_bilingual -> Native.

### Removed

- `position` on profile skills: dropped from `profile_skills`, from `ProfileSkillRead` and from
  `PATCH /profile/me/skills/{id}` (a `position` sent is ignored). Skills are listed by creation
  order and the CV orders them by evidence. The migration downgrade rebuilds `position` from
  the creation order.
- `classic` CV template: removed from the template registry. `?template=classic` now returns 404,
  and the default template (`/cv/settings`, `/cv/templates`) is `software-engineer`. A saved
  `preferred_template` of `classic` falls back to the default.
- **Breaking:** `category` on catalog skills: the `skills.category` column is dropped (the
  migration downgrade restores it empty), and `category` is gone from `SkillRead`,
  `POST /skills` and `PATCH /skills/{id}`, which now takes only `name` (required; 422 otherwise).

## [1.0.0] - 2026-10-02

### Added

- Users and profiles backed by Firebase authentication.
- CV data model and CRUD: experiences, educations, certifications, projects, links, languages and skills.
- Shared catalogs: companies, industries, skills and countries.
- CV download as PDF with selectable templates.
- CORS for the web app, configured with `CORS_ORIGINS`.
- Dockerfile and GitHub Actions workflows to deploy to Dokploy (staging and production).
