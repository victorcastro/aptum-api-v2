from typing import Protocol

from sqlalchemy.orm import Session

from aptum.modules.embeddings.service import EmbeddingClient
from aptum.modules.matching.repository import MatchingRepository
from aptum.modules.matching.schemas import MatchResult


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...


class NullLLMClient:
    def generate(self, prompt: str) -> str:
        return ""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


class MatchingService:
    def __init__(self, db: Session, embedding_client: EmbeddingClient, llm_client: LLMClient) -> None:
        self.repository = MatchingRepository(db)
        self.embedding_client = embedding_client
        self.llm_client = llm_client

    def match(self, user_id: int, job_description: str) -> MatchResult:
        profile_embedding = self.repository.get_profile_embedding(user_id)
        job_embedding = self.embedding_client.embed(job_description)

        score = (
            cosine_similarity(profile_embedding, job_embedding) if profile_embedding else 0.0
        )
        tailored_cv = self.llm_client.generate(
            f"Tailor this candidate's CV for the following job:\n{job_description}"
        )
        return MatchResult(score=score, tailored_cv=tailored_cv)
