from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aptum.modules.skill_categories.models import SkillCategory


class SkillCategoryRepository:
    """Every query is scoped to one profile."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for(self, profile_id: int) -> list[SkillCategory]:
        return (
            self.db.query(SkillCategory)
            .filter(SkillCategory.profile_id == profile_id)
            .order_by(SkillCategory.position, SkillCategory.id)
            .all()
        )

    def get_owned(self, profile_id: int, category_id: int) -> SkillCategory | None:
        return (
            self.db.query(SkillCategory)
            .filter(SkillCategory.profile_id == profile_id, SkillCategory.id == category_id)
            .first()
        )

    def next_position(self, profile_id: int) -> int:
        current = self.db.scalar(
            select(func.max(SkillCategory.position)).where(SkillCategory.profile_id == profile_id)
        )
        return (current or 0) + 1

    def create(self, profile_id: int, name: str, position: int) -> SkillCategory:
        """No commit. Flushes, so a name clash raises IntegrityError here."""
        category = SkillCategory(profile_id=profile_id, name=name, position=position)
        self.db.add(category)
        self.db.flush()
        return category

    def delete(self, category: SkillCategory) -> None:
        """No commit. The foreign key sets its profile skills' `category_id` to null (`Other`)."""
        self.db.delete(category)
