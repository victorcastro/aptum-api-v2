# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-10-03

ATS-friendly CV generation for English-speaking markets. Everything that changes the generated
CV is behind the `ATS_CV_ENABLED` feature flag, **off by default**: with it off, CV export
behaves exactly as in 1.0.0. Enable it with `ATS_CV_ENABLED=true`.

### Added

- Feature flag `ATS_CV_ENABLED` (setting `ats_cv_enabled`, default `false`).
- Skill categories: `profile_skills.category` with the values `LLMs & AI`, `Backend`,
  `Cloud & DevOps`, `Architecture`, `Mobile`, `Other`. Migration
  `0002_profile_skill_category` adds the column and backfills existing rows from a
  deterministic, versioned dictionary (`skills/data/skill_dictionary.json`, case-insensitive,
  with aliases; unknown skills go to `Other`).
- `category` (optional) on `POST/PATCH /profile/me/skills` and in skill responses; when omitted
  it is classified with the same dictionary (`null` on PATCH re-classifies).
- New profile fields, all optional: `linkedin_url`, `github_url`, `portfolio_url` (validated
  URLs), `english_level` (`A1`-`C2`, `Native`), `work_authorization` (`authorized`,
  `requires_sponsorship`), `work_authorization_country`, `open_to_relocation`; `area` on
  experiences (`backend`, `mobile`, `ai`, `other`); `start_year` / `end_year` on educations.
  Migration `0003_profile_ats_fields`.
- ATS PDF: single column, standard font, no tables/images/icons/lines/photo, selectable text,
  standard headings (Summary, Experience, Skills, Education, Certifications, Projects,
  Languages), `Mon YYYY - Mon YYYY` dates, at most 2 pages. The header prints the profile
  links as visible URLs and one work authorization line only when set; `english_level` is
  printed in Languages.
- Skills printed one line per category; with a job offer, up to 25 skills with offer-relevant
  ones first. Only skills from the profile are ever printed.
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
  `keyword_coverage`). Both return 404 while the flag is off.
- Duplicate education detection (same institution, overlapping titles) as a warning.
- Test suite (pytest, synthetic data only), run in CI.

### Changed

- With the flag on, `GET /cv/export` without a `template` parameter renders the ATS PDF;
  `?template=` still renders the legacy templates.
- With the flag on, the matching prompt includes the computed years of experience as locked
  facts.
- The OpenAPI metadata now reports the package version (`1.1.0`), read from `pyproject.toml`.

### Fixed

- Skill groups in the CV no longer depend on the free-text catalog category (`skills.category`)
  when the flag is on: every profile skill lands in one of the six standard groups.

## [1.0.0] - 2026-10-02

### Added

- Users and profiles backed by Firebase authentication.
- CV data model and CRUD: experiences, educations, certifications, projects, links, languages and skills.
- Shared catalogs: companies, industries, skills and countries.
- CV download as PDF with selectable templates.
- CORS for the web app, configured with `CORS_ORIGINS`.
- Dockerfile and GitHub Actions workflows to deploy to Dokploy (staging and production).
