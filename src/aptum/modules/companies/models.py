from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aptum.db.base import Base, TimestampMixin


class Industry(Base):
    __tablename__ = "industries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)


class Company(TimestampMixin, Base):
    """Shared catalog entry, not owned by any user. Used both as employer and as client."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True)
    industry_id: Mapped[int | None] = mapped_column(
        ForeignKey("industries.id", ondelete="SET NULL"), index=True, default=None
    )
    city: Mapped[str | None] = mapped_column(String(120), default=None)
    country_code: Mapped[str | None] = mapped_column(String(2), default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    logo_url: Mapped[str | None] = mapped_column(String(500), default=None)
    is_consultancy: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    industry: Mapped["Industry | None"] = relationship(lazy="joined")
