from fastapi import APIRouter

from aptum.common.countries import COUNTRIES
from aptum.modules.commons.schemas import CountryRead

router = APIRouter(prefix="/commons", tags=["commons"])

_COUNTRIES = [
    CountryRead(code=code, name=name)
    for code, name in sorted(COUNTRIES.items(), key=lambda item: item[1])
]


@router.get("/countries", response_model=list[CountryRead])
def list_countries():
    return _COUNTRIES
