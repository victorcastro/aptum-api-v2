from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from aptum.db.base import Base, TimestampMixin


class Skill(TimestampMixin, Base):
    """Shared catalog entry, not owned by any user."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
