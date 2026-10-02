from sqlalchemy.orm import Session

from aptum.common.utils import slugify
from aptum.core.exceptions import AptumError
from aptum.modules.skills.models import Skill
from aptum.modules.skills.repository import SkillRepository
from aptum.modules.skills.schemas import SkillCreate


class SkillService:
    def __init__(self, db: Session) -> None:
        self.repository = SkillRepository(db)

    def search(self, query: str, limit: int = 20) -> list[Skill]:
        return self.repository.search(query.strip(), limit)

    def get_or_create(self, user_id: int, data: SkillCreate) -> Skill:
        slug = slugify(data.name)
        if not slug:
            raise AptumError("Skill name must contain letters or numbers")
        existing = self.repository.get_by_slug(slug)
        if existing is not None:
            return existing
        return self.repository.create(
            name=data.name.strip(),
            slug=slug,
            category=data.category,
            created_by_user_id=user_id,
        )
