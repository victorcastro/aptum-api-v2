from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from aptum.db.base import Base


class Language(Base):
    """Languages a profile can list. `code` is ISO 639-1; `name` is in English."""

    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class LanguageLevel(Base):
    """CEFR levels plus Native, ordered by `rank`. `code` is what profiles store and the CV prints."""

    __tablename__ = "language_levels"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(255))
    rank: Mapped[int] = mapped_column(SmallInteger, unique=True)
