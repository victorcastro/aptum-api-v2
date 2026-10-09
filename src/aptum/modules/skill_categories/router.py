from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.skill_categories.schemas import (
    SkillCategoryCreate,
    SkillCategoryOrder,
    SkillCategoryRead,
    SkillCategoryUpdate,
)
from aptum.modules.skill_categories.service import SkillCategoryService
from aptum.modules.users.models import User

router = APIRouter(prefix="/profile/me/skill-categories", tags=["profile"])


@router.get("", response_model=list[SkillCategoryRead])
def list_my_skill_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The caller's CV skill groups in print order; `Other` (skills without a category) is not
    listed and always prints last. Empty without a profile. 401 bad token."""
    return SkillCategoryService(db).list_for(current_user.id)


@router.post("", response_model=SkillCategoryRead, status_code=201)
def create_my_skill_category(
    data: SkillCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adds a category at the end of the caller's order.

    400 name without letters or digits; 401 bad token; 404 no profile; 409 one of the caller's
    categories has the same normalized name; 422 name missing, empty or over 40 characters."""
    return SkillCategoryService(db).create(current_user.id, data)


@router.put("/order", response_model=list[SkillCategoryRead])
def reorder_my_skill_categories(
    data: SkillCategoryOrder,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sets the print order. `ids` must list every category of the caller exactly once.

    400 ids repeated, missing or not the caller's; 401 bad token; 404 no profile; 422 empty ids."""
    return SkillCategoryService(db).reorder(current_user.id, data)


@router.patch("/{category_id}", response_model=SkillCategoryRead)
def rename_my_skill_category(
    category_id: int,
    data: SkillCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Renames one of the caller's categories; its skills keep pointing at it.

    400 name without letters or digits; 401 bad token; 404 unknown or another user's category;
    409 another of the caller's categories has the same normalized name."""
    return SkillCategoryService(db).rename(current_user.id, category_id, data)


@router.delete("/{category_id}", status_code=204)
def delete_my_skill_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Deletes one of the caller's categories; its skills move to `Other`.

    401 bad token; 404 unknown or another user's category."""
    SkillCategoryService(db).delete(current_user.id, category_id)
    return Response(status_code=204)
