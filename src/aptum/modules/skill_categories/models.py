from sqlalchemy import Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column

from aptum.db.base import Base, TimestampMixin

OTHER_CATEGORY = "Other"


class SkillCategory(TimestampMixin, Base):
    """CV skill group. `position` is the order the CV prints them. The system category
    (`Other`) is where unclassified skills live and where a deleted category's skills go."""

    __tablename__ = "skill_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_system: Mapped[bool] = mapped_column(default=False, server_default=false())
