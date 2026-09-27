from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from aptum.core.security import decode_access_token
from aptum.db.session import SessionLocal
from aptum.modules.embeddings.service import EmbeddingClient, NullEmbeddingClient
from aptum.modules.matching.service import LLMClient, NullLLMClient
from aptum.modules.users.models import User
from aptum.modules.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc

    user = UserRepository(db).get_by_id(int(user_id))
    if user is None:
        raise credentials_error
    return user


def get_embedding_client() -> EmbeddingClient:
    return NullEmbeddingClient()


def get_llm_client() -> LLMClient:
    return NullLLMClient()
