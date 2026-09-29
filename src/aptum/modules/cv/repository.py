from sqlalchemy.orm import Session

from aptum.modules.cv.models import CVDocument


class CVRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_for_user(self, user_id: int) -> CVDocument | None:
        return (
            self.db.query(CVDocument)
            .filter(CVDocument.user_id == user_id)
            .order_by(CVDocument.id.desc())
            .first()
        )

    def create(self, user_id: int, filename: str, raw_text: str) -> CVDocument:
        cv = CVDocument(user_id=user_id, filename=filename, raw_text=raw_text)
        self.db.add(cv)
        self.db.commit()
        self.db.refresh(cv)
        return cv

    def set_embedding(self, cv: CVDocument, embedding: list[float]) -> CVDocument:
        cv.embedding = embedding
        self.db.commit()
        self.db.refresh(cv)
        return cv
