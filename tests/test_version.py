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
