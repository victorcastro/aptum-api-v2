from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.cv.schemas import CVSettingsRead, CVSettingsUpdate, CVTemplateOut
from aptum.modules.cv.service import CVService
from aptum.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("/templates", response_model=list[CVTemplateOut])
def list_cv_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CVService(db).list_templates(current_user.id)


@router.get("/settings", response_model=CVSettingsRead)
def read_cv_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CVService(db).get_settings(current_user.id)


@router.patch("/settings", response_model=CVSettingsRead)
def update_cv_settings(
    data: CVSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CVService(db).update_settings(current_user.id, data)


@router.delete("/settings", status_code=204)
def reset_cv_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    CVService(db).reset_settings(current_user.id)


@router.get(
    "/export",
    response_class=Response,
    responses={
        200: {
            "description": "CV as a PDF file",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
def export_cv(
    template: str | None = Query(default=None, description="Template for this download only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pdf, filename = CVService(db).export_pdf(current_user.id, template)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
