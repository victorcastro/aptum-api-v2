from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.profile.schemas import (
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    ProfileRead,
    ProfileUpdate,
)
from aptum.modules.profile.service import ProfileService
from aptum.modules.users.models import User

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=ProfileRead)
def read_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).get_or_create(current_user.id)


@router.patch("/me", response_model=ProfileRead)
def update_my_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update(current_user.id, data)


@router.post("/me/experiences", status_code=201)
def add_experience(
    data: ExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_experience(current_user.id, data)


@router.post("/me/educations", status_code=201)
def add_education(
    data: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_education(current_user.id, data)


@router.post("/me/languages", status_code=201)
def add_language(
    data: LanguageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_language(current_user.id, data)
