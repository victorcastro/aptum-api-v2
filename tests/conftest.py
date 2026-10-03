import os
import sys
from io import BytesIO
from pathlib import Path

# Settings require these; tests never connect to a database (except test_migrations, opt-in).
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:1/test")
os.environ.setdefault("FIREBASE_PROJECT_ID", "test")
sys.path.insert(0, str(Path(__file__).parent))

from pypdf import PdfReader


def pdf_text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
