from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from aptum.common.countries import COUNTRIES
from aptum.core.dependencies import get_db
from aptum.core.permissions import Permission, require
from aptum.modules.commons.repository import CommonsRepository
from aptum.modules.commons.schemas import (
    CountryRead,
    DegreeCreate,
    DegreeDetailRead,
    DegreeGroupRead,
    DegreeRead,
    DegreeUpdate,
    LanguageLevelOption,
    LanguageOption,
)
from aptum.modules.commons.service import CommonsService
from aptum.modules.users.models import User

router = APIRouter(prefix="/commons", tags=["commons"])

_COUNTRIES = [
    CountryRead(code=code, name=name)
    for code, name in sorted(COUNTRIES.items(), key=lambda item: item[1])
]


@router.get("/countries", response_model=list[CountryRead])
def list_countries():
    return _COUNTRIES


@router.get("/degrees", response_model=list[DegreeGroupRead])
def list_degrees(db: Session = Depends(get_db)):
    """Degrees an education can point to, grouped by level, in catalog order."""
    groups: dict[str, DegreeGroupRead] = {}
    for degree in CommonsRepository(db).list_degrees():
        group = groups.setdefault(degree.level, DegreeGroupRead(heading=degree.level, options=[]))
        group.options.append(DegreeRead.model_validate(degree))
    return list(groups.values())


@router.post("/degrees", response_model=DegreeDetailRead, status_code=201)
def create_degree(
    data: DegreeCreate,
    current_user: User = Depends(require(Permission.degree_manage)),
    db: Session = Depends(get_db),
):
    """Add a degree at the end of its level (a new level goes after the last one). Needs `degree:manage`. Audited.

    400 name or level without letters or digits; 401 bad token; 403 missing permission;
    409 a degree with the same normalized name exists."""
    return CommonsService(db).create_degree(current_user, data)


@router.patch("/degrees/{degree_id}", response_model=DegreeDetailRead)
def update_degree(
    degree_id: int,
    data: DegreeUpdate,
    current_user: User = Depends(require(Permission.degree_manage)),
    db: Session = Depends(get_db),
):
    """Rename a degree and/or move it to another level (it goes to the end of that level). Needs `degree:manage`. Audited.

    400 name or level without letters or digits; 401 bad token; 403 missing permission;
    404 unknown degree; 409 another degree has the same normalized name."""
    return CommonsService(db).update_degree(current_user, degree_id, data)


@router.delete("/degrees/{degree_id}", status_code=204)
def delete_degree(
    degree_id: int,
    current_user: User = Depends(require(Permission.degree_manage)),
    db: Session = Depends(get_db),
):
    """Delete a degree no education uses. Needs `degree:manage`. Audited.

    401 bad token; 403 missing permission; 404 unknown degree; 409 in use by educations."""
    CommonsService(db).delete_degree(current_user, degree_id)
    return Response(status_code=204)


@router.get("/languages", response_model=list[LanguageOption])
def list_languages(db: Session = Depends(get_db)):
    """Languages a profile can list, sorted by name."""
    return CommonsRepository(db).list_languages()


@router.get("/language-levels", response_model=list[LanguageLevelOption])
def list_language_levels(db: Session = Depends(get_db)):
    """Levels a language can have (CEFR plus Native), from lowest to highest."""
    return CommonsRepository(db).list_language_levels()
