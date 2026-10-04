from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.common.utils import slugify
from aptum.core.exceptions import AptumError, ConflictError, NotFoundError
from aptum.core.permissions import Actor
from aptum.modules.audit.service import AuditService, diff, snapshot
from aptum.modules.skills.models import Skill
from aptum.modules.skills.repository import SkillRepository
from aptum.modules.skills.schemas import SkillCreate, SkillUpdate


class SkillService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SkillRepository(db)
        self.audit = AuditService(db)

    def search(self, query: str, limit: int = 20) -> list[Skill]:
        return self.repository.search(query.strip(), limit)

    def list_page(self, limit: int, offset: int) -> list[Skill]:
        """The whole catalog in name order."""
        return self.repository.list_page(limit, offset)

    def get_or_create(self, user_id: int, data: SkillCreate) -> Skill:
        slug = _slug(data.name)
        existing = self.repository.get_by_slug(slug)
        if existing is not None:
            return existing
        try:
            skill = self.repository.create(name=data.name.strip(), slug=slug, created_by_user_id=user_id)
            self.db.commit()
        except IntegrityError:  # someone created the same skill meanwhile: return theirs
            self.db.rollback()
            existing = self.repository.get_by_slug(slug)
            if existing is None:
                raise
            return existing
        self.db.refresh(skill)
        return skill

    def update(self, actor: Actor, skill_id: int, data: SkillUpdate) -> Skill:
        """Rename a catalog skill; the slug follows (`skill:update_any`, checked by the router)."""
        skill = self.repository.get(skill_id)
        if skill is None:
            raise NotFoundError("Skill not found")
        name = data.name.strip()
        slug = _slug(name)
        clash = self.repository.get_by_slug(slug)
        if clash is not None and clash.id != skill.id:
            raise ConflictError("A skill with that name already exists")
        fields = {"name": name, "slug": slug}
        changes = diff(snapshot(skill, fields), fields)
        if not changes:
            return skill
        self.audit.record(actor.id, AuditAction.skill_update, AuditEntity.skill, skill.id, changes)
        self.repository.update(skill, **fields)
        try:
            self.db.commit()
        except IntegrityError as exc:  # concurrent rename to the same slug
            self.db.rollback()
            raise ConflictError("A skill with that name already exists") from exc
        self.db.refresh(skill)
        return skill


def _slug(name: str) -> str:
    slug = slugify(name)
    if not slug:
        raise AptumError("Skill name must contain letters or numbers")
    return slug
