from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aptum.common.constants import EMBEDDING_DIM
from aptum.db.base import Base, TimestampMixin


class CVDocument(TimestampMixin, Base):
    __tablename__ = "cv_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str | None] = mapped_column(Text, default=None)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
