"""Migrations against a real, throwaway Postgres with pgvector. Skipped unless MIGRATION_TEST_DATABASE_URL is set.

    docker run -d --rm --name aptum-pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=aptum \
        -p 55432:5432 pgvector/pgvector:pg18
    MIGRATION_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/aptum uv run pytest

The database is wiped (downgrade to base) at the start: never point this at real data.
"""

import os
import subprocess
from pathlib import Path

import pytest
import sqlalchemy as sa

URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(not URL, reason="MIGRATION_TEST_DATABASE_URL not set")


def alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": URL, "FIREBASE_PROJECT_ID": "test"}
    subprocess.run(["alembic", *args], cwd=ROOT, env=env, check=True, capture_output=True)


@pytest.fixture
def engine():
    alembic("downgrade", "base")
    alembic("upgrade", "0001")
    engine = sa.create_engine(URL)
    yield engine
    engine.dispose()


def _seed_v1(conn) -> None:
    conn.execute(sa.text("INSERT INTO users (id, email, is_active) VALUES (1, 'synthetic@example.com', true)"))
    conn.execute(sa.text("INSERT INTO profiles (id, user_id) VALUES (1, 1)"))
    conn.execute(sa.text("INSERT INTO companies (id, name, normalized_name, is_consultancy) VALUES (1, 'Acme', 'acme', false)"))
    names = ["openai", "FastAPI", "docker", "SWIFT", "Hexagonal Architecture", "COBOL", "rag", "Node.js"]
    for index, name in enumerate(names, start=1):
        conn.execute(
            sa.text("INSERT INTO skills (id, name, slug) VALUES (:id, :name, :slug)"),
            {"id": index, "name": name, "slug": f"s{index}"},
        )
        conn.execute(
            sa.text("INSERT INTO profile_skills (profile_id, skill_id, position) VALUES (1, :id, :pos)"),
            {"id": index, "pos": index},
        )
    conn.execute(sa.text(
        "INSERT INTO experiences (profile_id, position, employer_id, start_date, is_current) "
        "VALUES (1, 'Engineer', 1, '2020-01-01', true)"
    ))
    conn.execute(sa.text(
        "INSERT INTO educations (profile_id, institution, degree) VALUES (1, 'Uni', 'BSc')"
    ))


def test_upgrade_backfills_and_downgrade_round_trips(engine):
    with engine.begin() as conn:
        _seed_v1(conn)

    alembic("upgrade", "head")
    with engine.connect() as conn:
        categories = dict(conn.execute(sa.text(
            "SELECT s.name, ps.category FROM profile_skills ps JOIN skills s ON s.id = ps.skill_id"
        )).all())
        profile = conn.execute(sa.text("SELECT * FROM profiles WHERE id = 1")).mappings().one()
        experience = conn.execute(sa.text("SELECT * FROM experiences")).mappings().one()
    assert categories == {
        "openai": "LLMs & AI",
        "FastAPI": "Backend",
        "docker": "Cloud & DevOps",
        "SWIFT": "Mobile",
        "Hexagonal Architecture": "Architecture",
        "COBOL": "Other",
        "rag": "LLMs & AI",
        "Node.js": "Backend",
    }
    # New profile fields are optional: existing rows keep working with NULLs / defaults.
    assert profile["english_level"] is None and profile["open_to_relocation"] is False
    assert experience["area"] is None

    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        conn.execute(sa.text("UPDATE profile_skills SET category = 'Frontend' WHERE id = 1"))

    with engine.connect() as conn:
        columns = {row[0] for row in conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'profile_skills'"
        ))}
    assert "position" not in columns and "category" in columns

    alembic("check")  # models and migrations agree
    alembic("downgrade", "0001")
    with engine.connect() as conn:
        positions = conn.execute(sa.text("SELECT position FROM profile_skills ORDER BY id")).scalars().all()
    assert positions == list(range(8))  # rolled back without losing rows; position rebuilt from id order
    alembic("upgrade", "head")
