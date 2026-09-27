from io import BytesIO

from pypdf import PdfReader
from sqlalchemy.orm import Session

from aptum.modules.cv.repository import CVDocument, CVRepository


class CVService:
    def __init__(self, db: Session) -> None:
        self.repository = CVRepository(db)

    def upload(self, user_id: int, filename: str, content: bytes) -> CVDocument:
        raw_text = self._extract_text(content)
        return self.repository.create(user_id, filename, raw_text)

    def get_latest(self, user_id: int) -> CVDocument | None:
        return self.repository.get_latest_for_user(user_id)

    @staticmethod
    def _extract_text(content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
