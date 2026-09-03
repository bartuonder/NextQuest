from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.enums import Category


class Favorite(Base):
    """A single title the user loves, e.g. ("game", "Hollow Knight")."""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "category", "title", name="uq_favorite_per_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[Category] = mapped_column(
        SQLEnum(Category, native_enum=False, length=20), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship(back_populates="favorites")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Favorite {self.category}:{self.title!r}>"
