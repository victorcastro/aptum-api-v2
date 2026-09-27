from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.cv.schemas import CVRead
from aptum.modules.cv.service import CVService
from aptum.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/upload", response_model=CVRead, status_code=201)
async def upload_cv(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVRead:
    content = await file.read()
    return CVService(db).upload(current_user.id, file.filename, content)


@router.get("/latest", response_model=CVRead)
def read_latest_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVRead | None:
    return CVService(db).get_latest(current_user.id)
