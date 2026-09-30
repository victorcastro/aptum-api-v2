from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.cv.service import CVService
from aptum.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("/export", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def export_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pdf = CVService(db).export_pdf(current_user.id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="cv.pdf"'},
    )
