from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db, get_embedding_client, get_llm_client
from aptum.modules.embeddings.service import EmbeddingClient
from aptum.modules.matching.schemas import MatchRequest, MatchResult
from aptum.modules.matching.service import LLMClient, MatchingService
from aptum.modules.users.models import User

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/", response_model=MatchResult)
def match_job(
    data: MatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
    llm_client: LLMClient = Depends(get_llm_client),
) -> MatchResult:
    return MatchingService(db, embedding_client, llm_client).match(
        current_user.id, data.job_description
    )
