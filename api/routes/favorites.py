from fastapi import APIRouter, HTTPException, status

from api.deps import CurrentUser, DbSession
from schemas.favorite import FavoriteCreate, FavoriteRead, TasteProfile
from services import favorites as favorites_service

router = APIRouter(prefix="/favorites", tags=["favorites"])

# Starlette renamed HTTP_422_UNPROCESSABLE_ENTITY mid-2025; the number is the
# spelling that works on every supported version.
UNPROCESSABLE_CONTENT = 422


@router.get("", response_model=list[FavoriteRead])
def list_favorites(db: DbSession, user: CurrentUser) -> list[FavoriteRead]:
    return favorites_service.list_favorites(db, user)


@router.get("/taste", response_model=TasteProfile)
def read_taste(db: DbSession, user: CurrentUser) -> TasteProfile:
    """The saved favourites grouped the same way the questionnaire submits them."""
    return favorites_service.taste_from_favorites(
        favorites_service.list_favorites(db, user)
    )


@router.put("/taste", response_model=list[FavoriteRead])
def replace_taste(
    db: DbSession, user: CurrentUser, taste: TasteProfile
) -> list[FavoriteRead]:
    """Overwrite the whole profile with one questionnaire submission."""
    return favorites_service.replace_taste(db, user, taste)


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def add_favorite(
    db: DbSession, user: CurrentUser, data: FavoriteCreate
) -> FavoriteRead:
    try:
        return favorites_service.add_favorite(db, user, data)
    except favorites_service.DuplicateFavoriteError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except favorites_service.FavoriteLimitError as exc:
        raise HTTPException(UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(db: DbSession, user: CurrentUser, favorite_id: int) -> None:
    if not favorites_service.delete_favorite(db, user, favorite_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Favourite not found.")
