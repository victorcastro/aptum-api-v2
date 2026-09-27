from sqlalchemy.orm import Session

from aptum.modules.cv.repository import CVDocument
from aptum.modules.profile.models import Profile


class EmbeddingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def set_profile_embedding(self, profile_id: int, embedding: list[float]) -> None:
        profile = self.db.get(Profile, profile_id)
        profile.embedding = embedding
        self.db.commit()

    def set_cv_embedding(self, cv_id: int, embedding: list[float]) -> None:
        cv = self.db.get(CVDocument, cv_id)
        cv.embedding = embedding
        self.db.commit()

    def find_similar_profiles(self, embedding: list[float], limit: int = 10) -> list[Profile]:
        return (
            self.db.query(Profile)
            .order_by(Profile.embedding.cosine_distance(embedding))
            .limit(limit)
            .all()
        )
