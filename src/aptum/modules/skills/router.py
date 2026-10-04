from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.core.permissions import Permission, require
from aptum.modules.skills.schemas import SkillCreate, SkillRead, SkillUpdate
from aptum.modules.skills.service import SkillService
from aptum.modules.users.models import User

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillRead])
def search_skills(
    q: str = Query(min_length=1),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SkillService(db).search(q)


@router.post("", response_model=SkillRead, status_code=201)
def create_skill(
    data: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SkillService(db).get_or_create(current_user.id, data)


@router.patch("/{skill_id}", response_model=SkillRead)
def update_skill(
    skill_id: int,
    data: SkillUpdate,
    current_user: User = Depends(require(Permission.skill_update_any)),
    db: Session = Depends(get_db),
):
    """Rename a catalog skill; the slug follows. Needs `skill:update_any`. Audited.

    400 name without letters or digits; 401 bad token; 403 missing permission; 404 unknown skill;
    409 another skill has the same normalized name (slug); 422 name missing or null."""
    return SkillService(db).update(current_user, skill_id, data)
