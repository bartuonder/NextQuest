from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from core.enums import Category


class RecommendationBatch(Base):
    """One LLM run: the taste snapshot that produced it plus its results."""

    __tablename__ = "recommendation_batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    model: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    mood: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_favorites: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    user: Mapped["User"] = relationship(back_populates="recommendations")  # noqa: F821
    items: Mapped[list["RecommendationItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RecommendationItem.id",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<RecommendationBatch id={self.id} items={len(self.items)}>"


class RecommendationItem(Base):
    """A single suggested title inside a batch."""

    __tablename__ = "recommendation_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_batches.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[Category] = mapped_column(
        SQLEnum(Category, native_enum=False, length=20), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    batch: Mapped[RecommendationBatch] = relationship(back_populates="items")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<RecommendationItem {self.category}:{self.title!r}>"
