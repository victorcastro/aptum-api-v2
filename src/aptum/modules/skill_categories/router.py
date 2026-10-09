from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.core.permissions import Permission, require
from aptum.modules.skill_categories.schemas import (
    SkillCategoryCreate,
    SkillCategoryOrder,
    SkillCategoryRead,
    SkillCategoryUpdate,
)
from aptum.modules.skill_categories.service import SkillCategoryService
from aptum.modules.users.models import User

router = APIRouter(prefix="/skill-categories", tags=["skill categories"])


@router.get("", response_model=list[SkillCategoryRead])
def list_skill_categories(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """CV skill groups in the order the CV prints them. 401 bad token."""
    return SkillCategoryService(db).list_all()


@router.post("", response_model=SkillCategoryRead, status_code=201)
def create_skill_category(
    data: SkillCategoryCreate,
    current_user: User = Depends(require(Permission.skill_category_manage)),
    db: Session = Depends(get_db),
):
    """Adds a category at the end of the order. Needs `skill_category:manage`. Audited.

    400 name without letters or digits; 401 bad token; 403 missing permission; 409 a category
    has the same normalized name; 422 name missing, empty or over 40 characters."""
    return SkillCategoryService(db).create(current_user, data)


@router.put("/order", response_model=list[SkillCategoryRead])
def reorder_skill_categories(
    data: SkillCategoryOrder,
    current_user: User = Depends(require(Permission.skill_category_manage)),
    db: Session = Depends(get_db),
):
    """Sets the print order. `ids` must list every category exactly once. Needs
    `skill_category:manage`. Audited.

    400 ids repeated, missing or unknown; 401 bad token; 403 missing permission; 422 empty ids."""
    return SkillCategoryService(db).reorder(current_user, data)


@router.patch("/{category_id}", response_model=SkillCategoryRead)
def rename_skill_category(
    category_id: int,
    data: SkillCategoryUpdate,
    current_user: User = Depends(require(Permission.skill_category_manage)),
    db: Session = Depends(get_db),
):
    """Renames a category; profile skills keep pointing at it. Needs `skill_category:manage`. Audited.

    400 name without letters or digits; 401 bad token; 403 missing permission; 404 unknown
    category; 409 system category (`Other`) or another category has the same normalized name."""
    return SkillCategoryService(db).rename(current_user, category_id, data)


@router.delete("/{category_id}", status_code=204)
def delete_skill_category(
    category_id: int,
    current_user: User = Depends(require(Permission.skill_category_manage)),
    db: Session = Depends(get_db),
):
    """Deletes a category; its profile skills move to `Other`. Needs `skill_category:manage`. Audited.

    401 bad token; 403 missing permission; 404 unknown category; 409 system category (`Other`)."""
    SkillCategoryService(db).delete(current_user, category_id)
