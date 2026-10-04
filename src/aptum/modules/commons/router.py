from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aptum.common.countries import COUNTRIES
from aptum.core.dependencies import get_db
from aptum.modules.commons.repository import CommonsRepository
from aptum.modules.commons.schemas import (
    CountryRead,
    LanguageLevelOption,
    LanguageOption,
)

router = APIRouter(prefix="/commons", tags=["commons"])

_COUNTRIES = [
    CountryRead(code=code, name=name)
    for code, name in sorted(COUNTRIES.items(), key=lambda item: item[1])
]


@router.get("/countries", response_model=list[CountryRead])
def list_countries():
    return _COUNTRIES


@router.get("/languages", response_model=list[LanguageOption])
def list_languages(db: Session = Depends(get_db)):
    """Languages a profile can list, sorted by name."""
    return CommonsRepository(db).list_languages()


@router.get("/language-levels", response_model=list[LanguageLevelOption])
def list_language_levels(db: Session = Depends(get_db)):
    """Levels a language can have (CEFR plus Native), from lowest to highest."""
    return CommonsRepository(db).list_language_levels()
