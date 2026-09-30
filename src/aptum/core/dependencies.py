from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from aptum.core.firebase import verify_id_token
from aptum.db.session import SessionLocal
from aptum.modules.embeddings.service import EmbeddingClient, NullEmbeddingClient
from aptum.modules.matching.service import LLMClient, NullLLMClient
from aptum.modules.users.models import User
from aptum.modules.users.service import UserService

# Login happens client-side with the Firebase SDK; the API only receives the ID token.
bearer_scheme = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = verify_id_token(credentials.credentials)
    except Exception as exc:  # firebase_admin raises several types (invalid, expired, revoked)
        raise credentials_error from exc

    email = claims.get("email")
    if not email or not claims.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    user = UserService(db).get_or_create_from_firebase(claims["uid"], email)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


def get_embedding_client() -> EmbeddingClient:
    return NullEmbeddingClient()


def get_llm_client() -> LLMClient:
    return NullLLMClient()
