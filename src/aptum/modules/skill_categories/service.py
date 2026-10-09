from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aptum.common.utils import normalize_name, slugify
from aptum.core.exceptions import AptumError, ConflictError, NotFoundError
from aptum.modules.profile.models import Profile
from aptum.modules.profile.repository import ProfileRepository
from aptum.modules.skill_categories import policy
from aptum.modules.skill_categories.models import SkillCategory
from aptum.modules.skill_categories.repository import SkillCategoryRepository
from aptum.modules.skill_categories.schemas import (
    SkillCategoryCreate,
    SkillCategoryOrder,
    SkillCategoryUpdate,
)


class SkillCategoryService:
    """The caller's own skill categories. Another profile's category is 404."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SkillCategoryRepository(db)
        self.profiles = ProfileRepository(db)

    def list_for(self, user_id: int) -> list[SkillCategory]:
        profile = self.profiles.get_by_user_id(user_id)
        return [] if profile is None else self.repository.list_for(profile.id)

    def create(self, user_id: int, data: SkillCategoryCreate) -> SkillCategory:
        profile = self._profile(user_id)
        name = self._check_name(profile.id, data.name, None)
        category = self.repository.create(profile.id, name, self.repository.next_position(profile.id))
        return self._commit(category)

    def rename(self, user_id: int, category_id: int, data: SkillCategoryUpdate) -> SkillCategory:
        profile = self._profile(user_id)
        category = self._get(profile.id, category_id)
        name = self._check_name(profile.id, data.name, category.id)
        if name == category.name:
            return category
        category.name = name
        return self._commit(category)

    def reorder(self, user_id: int, data: SkillCategoryOrder) -> list[SkillCategory]:
        profile = self._profile(user_id)
        categories = self.repository.list_for(profile.id)
        policy.check_order(data.ids, [category.id for category in categories])
        by_id = {category.id: category for category in categories}
        for position, category_id in enumerate(data.ids, start=1):
            by_id[category_id].position = position
        self.db.commit()
        return self.repository.list_for(profile.id)

    def delete(self, user_id: int, category_id: int) -> None:
        """Its profile skills move to `Other` (null category) through the foreign key."""
        profile = self._profile(user_id)
        self.repository.delete(self._get(profile.id, category_id))
        self.db.commit()

    def _profile(self, user_id: int) -> Profile:
        profile = self.profiles.get_by_user_id(user_id)
        if profile is None:
            raise NotFoundError("Profile not found")
        return profile

    def _get(self, profile_id: int, category_id: int) -> SkillCategory:
        category = self.repository.get_owned(profile_id, category_id)
        if category is None:
            raise NotFoundError("Skill category not found")
        return category

    def _check_name(self, profile_id: int, name: str, category_id: int | None) -> str:
        """Clean name, or 400 without letters or digits, or 409 when another category of the
        profile has the same normalized name."""
        name = name.strip()
        if not slugify(name):
            raise AptumError("Skill category name must contain letters or numbers")
        for other in self.repository.list_for(profile_id):
            if other.id != category_id and normalize_name(other.name) == normalize_name(name):
                raise ConflictError("A skill category with that name already exists")
        return name

    def _commit(self, category: SkillCategory) -> SkillCategory:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("A skill category with that name already exists") from exc
        self.db.refresh(category)
        return category
