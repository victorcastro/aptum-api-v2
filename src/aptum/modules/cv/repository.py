from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from aptum.db.base import Base

EMBEDDING_DIM = 1536


class CVDocument(Base):
    __tablename__ = "cv_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str | None] = mapped_column(String, default=None)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)


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
