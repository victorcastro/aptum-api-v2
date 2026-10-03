import os
import sys
from io import BytesIO
from pathlib import Path

import pytest

# Settings require these; tests never connect to a database (except test_migrations, opt-in).
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:1/test")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test")
os.environ.pop("ATS_CV_ENABLED", None)
sys.path.insert(0, str(Path(__file__).parent))

from pypdf import PdfReader

from aptum.core.config import get_settings


@pytest.fixture
def set_flag(monkeypatch):
    def set_(enabled: bool) -> None:
        monkeypatch.setenv("ATS_CV_ENABLED", "true" if enabled else "false")
        get_settings.cache_clear()

    yield set_
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _flag_off_by_default(monkeypatch):
    monkeypatch.setenv("ATS_CV_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def pdf_text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
