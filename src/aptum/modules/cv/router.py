from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.cv.schemas import (
    ATSGenerateRequest,
    ATSReport,
    CVSettingsRead,
    CVSettingsUpdate,
    CVTemplateOut,
)
from aptum.modules.cv.service import CVService
from aptum.modules.users.models import User

router = APIRouter(prefix="/cv", tags=["cv"])

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_PDF_RESPONSE = {
    200: {
        "description": "CV as a PDF file",
        "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
    }
}


def _pdf(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
            "description": "CV as a PDF file, or as an editable Word file with format=docx",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                _DOCX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
def export_cv(
    template: str | None = Query(default=None, description="Template for this download only (PDF)"),
    format: Literal["pdf", "docx"] = Query(default="pdf", description="docx ignores template"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service = CVService(db)
    if format == "docx":
        content, filename = service.export_docx(current_user.id)
        media_type = _DOCX_MEDIA_TYPE
    else:
        content, filename = service.export_pdf(current_user.id, template)
        media_type = "application/pdf"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/ats/export",
    response_class=Response,
    responses=_PDF_RESPONSE,
)
def export_ats_cv(
    data: ATSGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """ATS-friendly PDF (release 1.1.0), optionally tailored to `job_description`."""
    result, filename = CVService(db).generate_ats(current_user.id, data.job_description)
    return _pdf(result.pdf, filename)


@router.post("/ats/report", response_model=ATSReport)
def ats_cv_report(
    data: ATSGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ATSReport:
    """Report for the same CV that POST /cv/ats/export renders with the same body: warnings
    (missing metrics, removed duplicates/filler, trimming), fidelity issues, years of
    experience, selected skills and, with `job_description`, the keyword coverage."""
    service = CVService(db)
    result, _ = service.generate_ats(current_user.id, data.job_description)
    return service.report(result)
