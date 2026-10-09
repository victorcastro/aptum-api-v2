from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aptum.db.base import Base

# Where a profile skill without a category is printed: always the last group.
OTHER_LABEL = "Other"


class SkillCategory(Base):
    """A CV skill group owned by one profile. `position` is the order the CV prints them;
    skills without a category go to `Other`, which is not a row and is printed last."""

    __tablename__ = "skill_categories"
    __table_args__ = (UniqueConstraint("profile_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    position: Mapped[int] = mapped_column(Integer, default=0)


def print_order(category: SkillCategory | None) -> tuple[int, int, int]:
    """Sort key for CV groups: the profile's categories by `position`, then `Other` (None)."""
    return (1, 0, 0) if category is None else (0, category.position, category.id)


def print_name(category: SkillCategory | None) -> str:
    return OTHER_LABEL if category is None else category.name
