from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.enums import AuditAction, AuditEntity
from aptum.common.utils import normalize_name, slugify
from aptum.core.exceptions import AptumError, ConflictError, NotFoundError
from aptum.core.permissions import Actor
from aptum.modules.audit.service import AuditService, diff, snapshot
from aptum.modules.skill_categories import policy
from aptum.modules.skill_categories.models import SkillCategory
from aptum.modules.skill_categories.repository import SkillCategoryRepository
from aptum.modules.skill_categories.schemas import (
    SkillCategoryCreate,
    SkillCategoryOrder,
    SkillCategoryUpdate,
)

_FIELDS = ("name", "position", "is_system")


class SkillCategoryService:
    """Writes need `skill_category:manage`, checked by the router."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SkillCategoryRepository(db)
        self.audit = AuditService(db)

    def list_all(self) -> list[SkillCategory]:
        return self.repository.list_all()

    def create(self, actor: Actor, data: SkillCategoryCreate) -> SkillCategory:
        name = self._check_name(data.name, None)
        category = self.repository.create(name, self.repository.next_position())
        self.audit.record(
            actor.id,
            AuditAction.skill_category_create,
            AuditEntity.skill_category,
            category.id,
            {field: {"before": None, "after": getattr(category, field)} for field in _FIELDS},
        )
        return self._commit(category)

    def rename(self, actor: Actor, category_id: int, data: SkillCategoryUpdate) -> SkillCategory:
        category = self._get(category_id)
        policy.check_rename(category)
        fields = {"name": self._check_name(data.name, category.id)}
        changes = diff(snapshot(category, fields), fields)
        if not changes:
            return category
        self.audit.record(actor.id, AuditAction.skill_category_update, AuditEntity.skill_category, category.id, changes)
        category.name = fields["name"]
        return self._commit(category)

    def reorder(self, actor: Actor, data: SkillCategoryOrder) -> list[SkillCategory]:
        categories = self.repository.list_all()
        policy.check_order(data.ids, [category.id for category in categories])
        by_id = {category.id: category for category in categories}
        for position, category_id in enumerate(data.ids, start=1):
            category = by_id[category_id]
            changes = diff(snapshot(category, ("position",)), {"position": position})
            if changes:
                self.audit.record(
                    actor.id, AuditAction.skill_category_reorder, AuditEntity.skill_category, category.id, changes
                )
                category.position = position
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Skill categories changed meanwhile; try again") from exc
        return self.repository.list_all()

    def delete(self, actor: Actor, category_id: int) -> None:
        """The category's profile skills move to `Other` in the same transaction."""
        category = self._get(category_id)
        policy.check_delete(category)
        other = self.repository.get_other()
        if other is None:
            raise ConflictError("The 'Other' category is missing")
        reassigned = self.repository.reassign_profile_skills(category.id, other.id)
        self.audit.record(
            actor.id,
            AuditAction.skill_category_delete,
            AuditEntity.skill_category,
            category.id,
            {
                "deleted": snapshot(category, _FIELDS),
                "reassigned_to": other.id,
                "reassigned_count": reassigned,
            },
        )
        try:
            self.repository.delete(category)
            self.db.commit()
        except IntegrityError as exc:  # a skill was assigned to it meanwhile
            self.db.rollback()
            raise ConflictError("Skill category is in use; try again") from exc

    def _get(self, category_id: int) -> SkillCategory:
        category = self.repository.get(category_id)
        if category is None:
            raise NotFoundError("Skill category not found")
        return category

    def _check_name(self, name: str, category_id: int | None) -> str:
        """Clean name, or 400 without letters or digits, or 409 when another category has the
        same normalized name. The list is tiny, so it is compared in memory."""
        name = name.strip()
        if not slugify(name):
            raise AptumError("Skill category name must contain letters or numbers")
        for other in self.repository.list_all():
            if other.id != category_id and normalize_name(other.name) == normalize_name(name):
                raise ConflictError("A skill category with that name already exists")
        return name

    def _commit(self, category: SkillCategory) -> SkillCategory:
        try:
            self.db.commit()
        except IntegrityError as exc:  # concurrent create or rename to the same name
            self.db.rollback()
            raise ConflictError("A skill category with that name already exists") from exc
        self.db.refresh(category)
        return category
