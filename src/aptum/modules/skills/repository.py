from sqlalchemy.orm import Session

from aptum.modules.skills.models import Skill


class SkillRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, skill_id: int) -> Skill | None:
        return self.db.get(Skill, skill_id)

    def get_by_slug(self, slug: str) -> Skill | None:
        return self.db.query(Skill).filter(Skill.slug == slug).first()

    def search(self, query: str, limit: int) -> list[Skill]:
        return (
            self.db.query(Skill)
            .filter(Skill.name.icontains(query, autoescape=True))
            .order_by(Skill.name)
            .limit(limit)
            .all()
        )

    def create(self, **fields) -> Skill:
        """No commit. Flushes, so a slug clash raises IntegrityError here."""
        skill = Skill(**fields)
        self.db.add(skill)
        self.db.flush()
        return skill

    def update(self, skill: Skill, **fields) -> Skill:
        """No commit."""
        for key, value in fields.items():
            setattr(skill, key, value)
        return skill
