# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/).

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

### Changed

- `GET /cv/export` without a `template` parameter now renders the ATS PDF for everyone, and the
  saved template preference (`/cv/settings`) no longer applies to it; `?template=` still renders
  the legacy templates.
- The matching prompt includes the computed years of experience as locked facts.
- The OpenAPI metadata now reports the package version (`1.1.0`), read from `pyproject.toml`.
- CV skill groups come from `profile_skills.category` (six standard groups)
  instead of the free-text catalog category (`skills.category`).
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

## [1.0.0] - 2026-10-02

### Added

- Users and profiles backed by Firebase authentication.
- CV data model and CRUD: experiences, educations, certifications, projects, links, languages and skills.
- Shared catalogs: companies, industries, skills and countries.
- CV download as PDF with selectable templates.
- CORS for the web app, configured with `CORS_ORIGINS`.
- Dockerfile and GitHub Actions workflows to deploy to Dokploy (staging and production).
