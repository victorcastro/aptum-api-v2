import tomllib
from pathlib import Path

from aptum.main import app


def test_api_metadata_version_matches_pyproject():
    pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    assert app.version == pyproject["project"]["version"]
    assert app.openapi()["info"]["version"] == pyproject["project"]["version"]


def test_changelog_has_entry_for_version():
    pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())
    changelog = (Path(__file__).parent.parent / "CHANGELOG.md").read_text()
    assert f"## [{pyproject['project']['version']}]" in changelog


def test_version_endpoint_requires_auth_and_returns_the_app_version():
    from fastapi.testclient import TestClient

    from aptum.core.dependencies import get_current_user

    client = TestClient(app)
    assert client.get("/version").status_code in (401, 403)
    app.dependency_overrides[get_current_user] = lambda: object()
    try:
        response = client.get("/version")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"version": app.version}
