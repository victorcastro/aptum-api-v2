from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.companies.schemas import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    IndustryRead,
)
from aptum.modules.companies.service import CompanyService
from aptum.modules.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def search_companies(
    q: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search by name. Each result says whether the caller may edit it (`can_edit`). 401 bad token."""
    service = CompanyService(db)
    return service.to_read(current_user, service.search(q))


@router.get("/industries", response_model=list[IndustryRead])
def list_industries(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).list_industries()


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
