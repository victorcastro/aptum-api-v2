from typing import Protocol

from sqlalchemy.orm import Session

from aptum.modules.embeddings.repository import EmbeddingsRepository


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> list[float]: ...


class NullEmbeddingClient:
    def embed(self, text: str) -> list[float]:
        return []


class EmbeddingsService:
    def __init__(self, db: Session, client: EmbeddingClient) -> None:
        self.repository = EmbeddingsRepository(db)
        self.client = client

    def embed_profile(self, profile_id: int, text: str) -> None:
        self.repository.set_profile_embedding(profile_id, self.client.embed(text))
