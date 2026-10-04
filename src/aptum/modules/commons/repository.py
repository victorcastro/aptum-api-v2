from sqlalchemy.orm import Session

from aptum.modules.commons.models import Language, LanguageLevel


class CommonsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_languages(self) -> list[Language]:
        return self.db.query(Language).order_by(Language.name).all()

    def list_language_levels(self) -> list[LanguageLevel]:
        return self.db.query(LanguageLevel).order_by(LanguageLevel.rank).all()

    def has_language(self, code: str) -> bool:
        return self.db.get(Language, code) is not None

    def has_language_level(self, code: str) -> bool:
        return self.db.get(LanguageLevel, code) is not None
