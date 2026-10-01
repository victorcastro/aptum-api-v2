from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.skills.schemas import SkillCreate, SkillRead
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
