# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-02

### Added

- Users and profiles backed by Firebase authentication.
- CV data model and CRUD: experiences, educations, certifications, projects, links, languages and skills.
- Shared catalogs: companies, industries, skills and countries.
- CV download as PDF with selectable templates.
- CORS for the web app, configured with `CORS_ORIGINS`.
- Dockerfile and GitHub Actions workflows to deploy to Dokploy (staging and production).
