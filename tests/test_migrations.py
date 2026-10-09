"""Migrations against a real, throwaway Postgres with pgvector. Skipped unless MIGRATION_TEST_DATABASE_URL is set.

    docker run -d --rm --name aptum-pg-test -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=aptum \
        -p 55432:5432 pgvector/pgvector:pg18
    MIGRATION_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/aptum uv run pytest

The database is wiped (downgrade to base) at the start: never point this at real data.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa

URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(not URL, reason="MIGRATION_TEST_DATABASE_URL not set")


def _run(*command: str) -> None:
    env = {**os.environ, "DATABASE_URL": URL, "FIREBASE_PROJECT_ID": "test"}
    subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True)


def alembic(*args: str) -> None:
    _run("alembic", *args)


def roles_sync() -> None:
    _run(sys.executable, "-m", "aptum.modules.roles.sync")


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
    conn.execute(sa.text("INSERT INTO users (id, email, is_active) VALUES (2, 'synthetic2@example.com', true)"))
    conn.execute(sa.text("INSERT INTO profiles (id, user_id) VALUES (2, 2)"))
    conn.execute(sa.text(
        "INSERT INTO profile_languages (profile_id, language_code, proficiency) VALUES "
        "(1, 'es', 'native_or_bilingual'), (1, 'en', 'full_professional'), (1, 'no', 'limited_working'), "
        "(2, 'pt', 'elementary')"
    ))


def test_upgrade_backfills_and_downgrade_round_trips(engine):
    with engine.begin() as conn:
        _seed_v1(conn)

    alembic("upgrade", "0002")
    with engine.connect() as conn:
        roles = conn.execute(sa.text("SELECT role FROM users ORDER BY id")).scalars().all()
    assert roles == ["user", "user"]  # existing users get the safe default
    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        conn.execute(sa.text("UPDATE users SET role = 'root' WHERE id = 1"))
    with engine.begin() as conn:
        conn.execute(sa.text("UPDATE users SET role = 'moderator' WHERE id = 2"))

    alembic("upgrade", "head")
    with engine.connect() as conn:
        categories = dict(conn.execute(sa.text(
            "SELECT s.name, sc.name FROM profile_skills ps JOIN skills s ON s.id = ps.skill_id "
            "JOIN skill_categories sc ON sc.id = ps.category_id"
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
    assert profile["open_to_relocation"] is False
    assert experience["area"] is None

    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        conn.execute(sa.text("UPDATE profile_skills SET category_id = 999 WHERE id = 1"))
    with engine.connect() as conn:
        seeded = conn.execute(sa.text("SELECT name, position, is_system FROM skill_categories ORDER BY position")).all()
    assert seeded == [
        ("LLMs & AI", 1, False),
        ("Backend", 2, False),
        ("Cloud & DevOps", 3, False),
        ("Architecture", 4, False),
        ("Mobile", 5, False),
        ("Other", 6, True),
    ]

    with engine.connect() as conn:
        columns = {row[0] for row in conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'profile_skills'"
        ))}
    assert "position" not in columns and "category_id" in columns and "category" not in columns

    with engine.connect() as conn:
        languages = set(conn.execute(sa.text(
            "SELECT profile_id, language_code, proficiency FROM profile_languages"
        )).all())
        names = dict(conn.execute(sa.text("SELECT code, name FROM languages")).all())
        levels = conn.execute(sa.text("SELECT code FROM language_levels ORDER BY rank")).scalars().all()
    assert languages == {(1, "es", "Native"), (1, "en", "C1"), (1, "no", "B1"), (2, "pt", "A2")}
    assert names["es"] == "Spanish" and names["no"] == "NO"  # stored code missing from the seed
    assert levels == ["A1", "A2", "B1", "B2", "C1", "C2", "Native"]
    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        conn.execute(sa.text("UPDATE profile_languages SET proficiency = 'B3' WHERE profile_id = 2"))

    # 0003: roles in tables, every user keeps theirs.
    with engine.connect() as conn:
        user_roles = conn.execute(sa.text(
            "SELECT r.name FROM users u JOIN roles r ON r.id = u.role_id ORDER BY u.id"
        )).scalars().all()
        grants = conn.execute(sa.text(
            "SELECT r.name, count(rp.permission_id) FROM roles r "
            "LEFT JOIN role_permissions rp ON rp.role_id = r.id GROUP BY r.name"
        )).all()
        permission_count = conn.execute(sa.text("SELECT count(*) FROM permissions")).scalar()
    assert user_roles == ["user", "moderator"]
    assert dict(grants) == {"user": 0, "moderator": 6, "admin": permission_count}
    with engine.begin() as conn, pytest.raises(sa.exc.IntegrityError):
        conn.execute(sa.text("DELETE FROM roles WHERE name = 'moderator'"))  # still assigned

    # The migration seeds what the code wants: the first sync has nothing to do.
    roles_sync()
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT count(*) FROM audit_logs")).scalar() == 0
        assert conn.execute(sa.text("SELECT count(*) FROM permissions")).scalar() == permission_count

    # A custom role, to check the downgrade folds its users back to 'user'.
    with engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO roles (name, description) VALUES ('auditor', '')"))
        conn.execute(sa.text("UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'auditor') WHERE id = 1"))

    with engine.connect() as conn:
        tables = set(conn.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
    assert "audit_logs" in tables

    alembic("check")  # models and migrations agree
    with engine.begin() as conn:  # a category created after the upgrade folds into 'Other' on the way down
        conn.execute(sa.text("INSERT INTO skill_categories (name, position) VALUES ('Data', 7)"))
        conn.execute(sa.text(
            "UPDATE profile_skills SET category_id = (SELECT id FROM skill_categories WHERE name = 'Data') "
            "WHERE skill_id = (SELECT id FROM skills WHERE name = 'FastAPI')"
        ))
    alembic("downgrade", "0007")
    with engine.connect() as conn:
        old_categories = dict(conn.execute(sa.text(
            "SELECT s.name, ps.category FROM profile_skills ps JOIN skills s ON s.id = ps.skill_id"
        )).all())
    assert old_categories["FastAPI"] == "Other" and old_categories["docker"] == "Cloud & DevOps"
    alembic("upgrade", "head")
    alembic("downgrade", "0002")
    with engine.connect() as conn:
        roles = conn.execute(sa.text("SELECT role FROM users ORDER BY id")).scalars().all()
        tables = set(conn.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
    assert roles == ["user", "moderator"]  # the custom role folds back to the default
    assert not {"roles", "permissions", "role_permissions"} & tables

    alembic("downgrade", "0001")
    with engine.connect() as conn:
        tables = set(conn.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
        user_columns = set(conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
        )).scalars())
    assert "audit_logs" not in tables and "role" not in user_columns
    with engine.connect() as conn:
        positions = conn.execute(sa.text("SELECT position FROM profile_skills ORDER BY id")).scalars().all()
    assert positions == list(range(8))  # rolled back without losing rows; position rebuilt from id order
    with engine.connect() as conn:
        old_levels = set(conn.execute(sa.text(
            "SELECT profile_id, language_code, proficiency::text FROM profile_languages"
        )).all())
    assert old_levels == {
        (1, "es", "native_or_bilingual"),
        (1, "en", "full_professional"),
        (1, "no", "limited_working"),
        (2, "pt", "elementary"),
    }
    alembic("upgrade", "head")
