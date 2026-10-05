from types import SimpleNamespace

import pytest
from factories import FakeSession
from fastapi.testclient import TestClient

from aptum.core.dependencies import get_db
from aptum.core.exceptions import NotFoundError
from aptum.main import app
from aptum.modules.commons.models import Language, LanguageLevel
from aptum.modules.commons.repository import CommonsRepository
from aptum.modules.profile.models import ProfileLanguage
from aptum.modules.profile.schemas import LanguageCreate, LanguageUpdate
from aptum.modules.profile.service import ProfileService

LANGUAGES = {"en": "English", "es": "Spanish"}
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2", "Native")


class _FakeRepo:
    def __init__(self):
        self.saved: dict = {}

    def get_by_user_id(self, user_id):
        return SimpleNamespace(languages=[], skills=[])

    def add_row(self, model, profile, **fields):
        self.saved = fields
        return fields

    def get_row(self, model, profile, row_id):
        return SimpleNamespace()

    def update_row(self, row, **fields):
        self.saved = fields
        return fields


def _service() -> ProfileService:
    service = ProfileService.__new__(ProfileService)
    service.db = FakeSession()
    service.repository = _FakeRepo()
    service.commons = SimpleNamespace(
        has_language=lambda code: code in LANGUAGES,
        has_language_level=lambda code: code in LEVELS,
    )
    return service


def test_add_language_with_catalog_codes():
    service = _service()
    service.add_row(1, ProfileLanguage, LanguageCreate(language_code="en", proficiency="B2"))
    assert service.repository.saved == {"language_code": "en", "proficiency": "B2", "is_active": True}


@pytest.mark.parametrize(
    ("code", "level", "detail"),
    [("xx", "B2", "Language not found"), ("en", "B3", "Language level not found")],
)
def test_add_language_outside_the_catalog_is_404(code, level, detail):
    with pytest.raises(NotFoundError, match=detail):
        _service().add_row(1, ProfileLanguage, LanguageCreate(language_code=code, proficiency=level))


def test_update_level_is_checked_against_the_catalog():
    service = _service()
    service.update_row(1, ProfileLanguage, 5, LanguageUpdate(proficiency="C1"))
    assert service.repository.saved == {"proficiency": "C1"}
    with pytest.raises(NotFoundError, match="Language level not found"):
        service.update_row(1, ProfileLanguage, 5, LanguageUpdate(proficiency="Z9"))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        CommonsRepository,
        "list_languages",
        lambda self: [Language(code=code, name=name) for code, name in LANGUAGES.items()],
    )
    monkeypatch.setattr(
        CommonsRepository,
        "list_language_levels",
        lambda self: [
            LanguageLevel(code=code, name=f"Level {code}", description="...", rank=rank)
            for rank, code in enumerate(LEVELS, start=1)
        ],
    )
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_commons_languages_endpoint(client):
    assert client.get("/commons/languages").json() == [
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
    ]


def test_commons_language_levels_endpoint(client):
    levels = client.get("/commons/language-levels").json()
    assert [level["code"] for level in levels] == list(LEVELS)
    assert set(levels[0]) == {"code", "name", "description"}
