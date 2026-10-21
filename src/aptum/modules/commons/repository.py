from sqlalchemy import exists
from sqlalchemy.orm import Session

from aptum.modules.commons.models import Degree, Language, LanguageLevel
from aptum.modules.profile.models import Education


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

    def list_degrees(self) -> list[Degree]:
        return self.db.query(Degree).order_by(Degree.rank).all()

    def has_degree(self, degree_id: int) -> bool:
        return self.db.get(Degree, degree_id) is not None

    def get_degree(self, degree_id: int) -> Degree | None:
        return self.db.get(Degree, degree_id)

    def degree_in_use(self, degree_id: int) -> bool:
        return self.db.query(exists().where(Education.degree_id == degree_id)).scalar()

    def create_degree(self, name: str, level: str) -> Degree:
        """No commit. Rank 0 is a placeholder (real ranks start at 1) until `renumber_degrees` places it."""
        degree = Degree(name=name, level=level, rank=0)
        self.db.add(degree)
        self.db.flush()
        return degree

    def delete_degree(self, degree: Degree) -> None:
        """No commit."""
        self.db.delete(degree)
        self.db.flush()

    def renumber_degrees(self, ordered: list[Degree]) -> None:
        """Give `ordered` the ranks 1..n. No commit. `rank` is unique, so every stored rank is first
        made negative to leave room for any new numbering."""
        self.db.query(Degree).filter(Degree.rank > 0).update({Degree.rank: -Degree.rank}, synchronize_session="fetch")
        for rank, degree in enumerate(ordered, start=1):
            degree.rank = rank
        self.db.flush()
