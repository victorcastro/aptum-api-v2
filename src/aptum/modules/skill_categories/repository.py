from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from aptum.modules.profile.models import ProfileSkill
from aptum.modules.skill_categories.models import OTHER_CATEGORY, SkillCategory


class SkillCategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[SkillCategory]:
        return self.db.query(SkillCategory).order_by(SkillCategory.position, SkillCategory.id).all()

    def get(self, category_id: int) -> SkillCategory | None:
        return self.db.get(SkillCategory, category_id)

    def get_other(self) -> SkillCategory | None:
        return (
            self.db.query(SkillCategory)
            .filter(SkillCategory.is_system.is_(True), SkillCategory.name == OTHER_CATEGORY)
            .first()
        )

    def next_position(self) -> int:
        return (self.db.scalar(select(func.max(SkillCategory.position))) or 0) + 1

    def create(self, name: str, position: int) -> SkillCategory:
        """No commit. Flushes, so a name clash raises IntegrityError here."""
        category = SkillCategory(name=name, position=position)
        self.db.add(category)
        self.db.flush()
        return category

    def reassign_profile_skills(self, from_id: int, to_id: int) -> int:
        """No commit. Moves every profile skill of one category to another; returns how many."""
        result = self.db.execute(
            update(ProfileSkill).where(ProfileSkill.category_id == from_id).values(category_id=to_id)
        )
        return result.rowcount or 0

    def delete(self, category: SkillCategory) -> None:
        """No commit. Flushes, so the RESTRICT foreign key fails here if skills still point at it."""
        self.db.delete(category)
        self.db.flush()
