from sqlalchemy.orm import Session

from aptum.modules.profile.models import Profile


class EmbeddingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def set_profile_embedding(self, profile_id: int, embedding: list[float]) -> None:
        """No commit."""
        profile = self.db.get(Profile, profile_id)
        profile.embedding = embedding

    def find_similar_profiles(self, embedding: list[float], limit: int = 10) -> list[Profile]:
        return (
            self.db.query(Profile)
            .order_by(Profile.embedding.cosine_distance(embedding))
            .limit(limit)
            .all()
        )
