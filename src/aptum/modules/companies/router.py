from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.companies.schemas import CompanyCreate, CompanyRead, IndustryRead
from aptum.modules.companies.service import CompanyService
from aptum.modules.users.models import User

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def search_companies(
    q: str = Query(min_length=1),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CompanyService(db).search(q)


@router.get("/industries", response_model=list[IndustryRead])
def list_industries(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CompanyService(db).list_industries()


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get-or-create by normalized name, so 'BCP' typed twice never duplicates."""
    return CompanyService(db).get_or_create(current_user.id, data)
