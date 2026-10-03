from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from aptum.core.dependencies import get_current_user, get_db
from aptum.modules.profile.models import (
    Certification,
    Education,
    ProfileLanguage,
    ProfileLink,
    ProfileSkill,
    Project,
)
from aptum.modules.profile.schemas import (
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    EducationCreate,
    EducationRead,
    EducationUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    LanguageCreate,
    LanguageRead,
    LanguageUpdate,
    ProfileLinkCreate,
    ProfileLinkRead,
    ProfileLinkUpdate,
    ProfileRead,
    ProfileSkillCreate,
    ProfileSkillRead,
    ProfileSkillsGrouped,
    ProfileSkillUpdate,
    ProfileUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
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


@router.get("/me/experiences", response_model=list[ExperienceRead])
def list_experiences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_experiences(current_user.id)


@router.post("/me/experiences", response_model=ExperienceRead, status_code=201)
def add_experience(
    data: ExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_experience(current_user.id, data)


@router.patch("/me/experiences/{experience_id}", response_model=ExperienceRead)
def update_experience(
    experience_id: int,
    data: ExperienceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_experience(current_user.id, experience_id, data)


@router.delete("/me/experiences/{experience_id}", status_code=204)
def delete_experience(
    experience_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_experience(current_user.id, experience_id)
    return Response(status_code=204)


@router.get("/me/educations", response_model=list[EducationRead])
def list_educations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_rows(current_user.id, Education)


@router.post("/me/educations", response_model=EducationRead, status_code=201)
def add_education(
    data: EducationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_row(current_user.id, Education, data)


@router.patch("/me/educations/{education_id}", response_model=EducationRead)
def update_education(
    education_id: int,
    data: EducationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_row(current_user.id, Education, education_id, data)


@router.delete("/me/educations/{education_id}", status_code=204)
def delete_education(
    education_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_row(current_user.id, Education, education_id)
    return Response(status_code=204)


@router.get("/me/certifications", response_model=list[CertificationRead])
def list_certifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_rows(current_user.id, Certification)


@router.post("/me/certifications", response_model=CertificationRead, status_code=201)
def add_certification(
    data: CertificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_row(current_user.id, Certification, data)


@router.patch("/me/certifications/{certification_id}", response_model=CertificationRead)
def update_certification(
    certification_id: int,
    data: CertificationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_row(current_user.id, Certification, certification_id, data)


@router.delete("/me/certifications/{certification_id}", status_code=204)
def delete_certification(
    certification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_row(current_user.id, Certification, certification_id)
    return Response(status_code=204)


@router.get("/me/projects", response_model=list[ProjectRead])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_rows(current_user.id, Project)


@router.post("/me/projects", response_model=ProjectRead, status_code=201)
def add_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_row(current_user.id, Project, data)


@router.patch("/me/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_row(current_user.id, Project, project_id, data)


@router.delete("/me/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_row(current_user.id, Project, project_id)
    return Response(status_code=204)


@router.get("/me/links", response_model=list[ProfileLinkRead])
def list_links(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_rows(current_user.id, ProfileLink)


@router.post("/me/links", response_model=ProfileLinkRead, status_code=201)
def add_link(
    data: ProfileLinkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_row(current_user.id, ProfileLink, data)


@router.patch("/me/links/{link_id}", response_model=ProfileLinkRead)
def update_link(
    link_id: int,
    data: ProfileLinkUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_row(current_user.id, ProfileLink, link_id, data)


@router.delete("/me/links/{link_id}", status_code=204)
def delete_link(
    link_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_row(current_user.id, ProfileLink, link_id)
    return Response(status_code=204)


@router.get("/me/languages", response_model=list[LanguageRead])
def list_languages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_rows(current_user.id, ProfileLanguage)


@router.post("/me/languages", response_model=LanguageRead, status_code=201)
def add_language(
    data: LanguageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_row(current_user.id, ProfileLanguage, data)


@router.patch("/me/languages/{language_id}", response_model=LanguageRead)
def update_language(
    language_id: int,
    data: LanguageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_row(current_user.id, ProfileLanguage, language_id, data)


@router.delete("/me/languages/{language_id}", status_code=204)
def delete_language(
    language_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_row(current_user.id, ProfileLanguage, language_id)
    return Response(status_code=204)


@router.get("/me/skills", response_model=list[ProfileSkillRead])
def list_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_rows(current_user.id, ProfileSkill)


@router.get("/me/skills/grouped", response_model=ProfileSkillsGrouped)
def list_skills_grouped(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).list_skills_grouped(current_user.id)


@router.post("/me/skills", response_model=ProfileSkillRead, status_code=201)
def add_skill(
    data: ProfileSkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).add_row(current_user.id, ProfileSkill, data)


@router.patch("/me/skills/{profile_skill_id}", response_model=ProfileSkillRead)
def update_skill(
    profile_skill_id: int,
    data: ProfileSkillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_row(current_user.id, ProfileSkill, profile_skill_id, data)


@router.delete("/me/skills/{profile_skill_id}", status_code=204)
def delete_skill(
    profile_skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ProfileService(db).delete_row(current_user.id, ProfileSkill, profile_skill_id)
    return Response(status_code=204)
