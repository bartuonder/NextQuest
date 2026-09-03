"""Glue between the LLM engine and the recommendation history tables."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import Category
from models import RecommendationBatch, RecommendationItem, User
from schemas.favorite import TasteProfile
from schemas.recommendation import RecommendationRequest
from services import favorites as favorites_service
from services.llm_engine import LLMEngineError, RecommendationEngine


def resolve_taste(
    db: Session, user: User, request: RecommendationRequest
) -> TasteProfile:
    """Use the inline questionnaire when present, otherwise the saved favourites."""
    if request.taste is not None and request.taste.as_favorites():
        if request.save_favorites:
            favorites_service.replace_taste(db, user, request.taste)
        return request.taste
    return favorites_service.taste_from_favorites(
        favorites_service.list_favorites(db, user)
    )


def generate_batch(
    db: Session,
    user: User,
    request: RecommendationRequest,
    engine: RecommendationEngine,
) -> RecommendationBatch:
    taste = resolve_taste(db, user, request)
    if not taste.as_favorites():
        raise LLMEngineError(
            "Add at least one favourite title before asking for recommendations."
        )

    result = engine.generate(
        taste=taste,
        categories=request.categories,
        per_category=request.per_category,
        mood=request.mood,
    )

    batch = RecommendationBatch(
        user_id=user.id,
        model=engine.model_name,
        summary=result.summary,
        mood=request.mood,
        source_favorites=_snapshot(taste),
        items=[
            RecommendationItem(
                category=item.category,
                title=item.title,
                year=item.year,
                reason=item.reason,
                match_score=item.match_score,
                tags=item.tags,
            )
            for item in result.recommendations
        ],
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def list_batches(db: Session, user: User, limit: int = 20) -> list[RecommendationBatch]:
    stmt = (
        select(RecommendationBatch)
        .where(RecommendationBatch.user_id == user.id)
        .order_by(RecommendationBatch.created_at.desc(), RecommendationBatch.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_batch(db: Session, user: User, batch_id: int) -> RecommendationBatch | None:
    batch = db.get(RecommendationBatch, batch_id)
    if batch is None or batch.user_id != user.id:
        return None
    return batch


def delete_batch(db: Session, user: User, batch_id: int) -> bool:
    batch = get_batch(db, user, batch_id)
    if batch is None:
        return False
    db.delete(batch)
    db.commit()
    return True


def _snapshot(taste: TasteProfile) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for category, title in taste.as_favorites():
        snapshot.setdefault(Category(category).value, []).append(title)
    return snapshot
