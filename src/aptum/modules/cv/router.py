from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.cv.schemas import CVTemplateChoice, CVTemplateOut
from aptum.modules.cv.service import CVService
from aptum.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("/templates", response_model=list[CVTemplateOut])
def list_cv_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CVService(db).list_templates(current_user.id)


@router.put("/template", response_model=list[CVTemplateOut])
def set_cv_template(
    data: CVTemplateChoice,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CVService(db).set_preferred_template(current_user.id, data.template_id)


@router.get("/export", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def export_cv(
    template: str | None = Query(default=None, description="Template for this download only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pdf = CVService(db).export_pdf(current_user.id, template)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="cv.pdf"'},
    )
