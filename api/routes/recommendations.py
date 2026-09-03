from fastapi import APIRouter, HTTPException, Query, status

from api.deps import CurrentUser, DbSession, Engine
from schemas.recommendation import RecommendationBatchRead, RecommendationRequest
from services import recommendations as recommendations_service
from services.llm_engine import LLMEngineError, LLMNotConfiguredError

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationBatchRead, status_code=status.HTTP_201_CREATED)
def generate(
    db: DbSession, user: CurrentUser, engine: Engine, request: RecommendationRequest
) -> RecommendationBatchRead:
    try:
        return recommendations_service.generate_batch(db, user, request, engine)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except LLMEngineError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("", response_model=list[RecommendationBatchRead])
def list_batches(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[RecommendationBatchRead]:
    return recommendations_service.list_batches(db, user, limit=limit)


@router.get("/{batch_id}", response_model=RecommendationBatchRead)
def get_batch(
    db: DbSession, user: CurrentUser, batch_id: int
) -> RecommendationBatchRead:
    batch = recommendations_service.get_batch(db, user, batch_id)
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation batch not found.")
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(db: DbSession, user: CurrentUser, batch_id: int) -> None:
    if not recommendations_service.delete_batch(db, user, batch_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation batch not found.")
