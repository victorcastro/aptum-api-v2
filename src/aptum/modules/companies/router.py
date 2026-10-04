from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.core.permissions import Permission, require
from aptum.modules.companies.schemas import (
    CompanyCreate,
    CompanyMerge,
    CompanyRead,
    CompanyUpdate,
    IndustryRead,
    IndustryWrite,
)
from aptum.modules.companies.service import CompanyService
from aptum.modules.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def search_companies(
    q: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search by name (top 20). Without `q`, the whole catalog in name order, paged by `limit` and
    `offset`. Each result says whether the caller may edit it (`can_edit`). 401 bad token."""
    service = CompanyService(db)
    companies = service.search(q) if q is not None else service.list_page(limit, offset)
    return service.to_read(current_user, companies)


@router.get("/industries", response_model=list[IndustryRead])
def list_industries(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).list_industries()


@router.post("/industries", response_model=IndustryRead, status_code=201)
def create_industry(
    data: IndustryWrite,
    current_user: User = Depends(require(Permission.industry_manage)),
    db: Session = Depends(get_db),
):
    """Add an industry. Needs `industry:manage`. Audited.

    400 name without letters or digits; 401 bad token; 403 missing permission;
    409 an industry with the same normalized name exists."""
    return CompanyService(db).create_industry(current_user, data.name)


@router.patch("/industries/{industry_id}", response_model=IndustryRead)
def rename_industry(
    industry_id: int,
    data: IndustryWrite,
    current_user: User = Depends(require(Permission.industry_manage)),
    db: Session = Depends(get_db),
):
    """Rename an industry; the slug follows. Needs `industry:manage`. Audited.

    400 name without letters or digits; 401 bad token; 403 missing permission;
    404 unknown industry; 409 another industry has the same normalized name."""
    return CompanyService(db).rename_industry(current_user, industry_id, data.name)


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get-or-create by normalized name, so 'BCP' typed twice never duplicates.

    401 bad token; 404 unknown industry_id."""
    service = CompanyService(db)
    return service.to_read(current_user, [service.get_or_create(current_user.id, data)])[0]


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partial edit. `company:update_any` (moderator, admin): any company. Creator: only while
    no experience uses it.

    401 bad token; 403 creator but the company is in use; 404 unknown company or not yours;
    409 name clashes with another company or a required field sent as null."""
    service = CompanyService(db)
    return service.to_read(current_user, [service.update(current_user, company_id, data)])[0]


@router.post("/{company_id}/merge", response_model=CompanyRead)
def merge_company(
    company_id: int,
    data: CompanyMerge,
    current_user: User = Depends(require(Permission.company_merge)),
    db: Session = Depends(get_db),
):
    """Merge duplicate `company_id` into `target_id`: every experience pointing at it (as
    employer or client) moves to the target, then the duplicate is deleted. One transaction.
    A client equal to its employer after the move is cleared. Needs `company:merge`. Audited
    with a snapshot of the deleted company. Returns the target.

    401 bad token; 403 missing permission; 404 either company unknown; 409 same company."""
    service = CompanyService(db)
    return service.to_read(current_user, [service.merge(current_user, company_id, data.target_id)])[0]


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: int,
    current_user: User = Depends(require(Permission.company_delete)),
    db: Session = Depends(get_db),
):
    """Delete a company no experience uses. Needs `company:delete`. Audited.

    401 bad token; 403 missing permission; 404 unknown company; 409 in use (merge it instead)."""
    CompanyService(db).delete(current_user, company_id)
    return Response(status_code=204)
