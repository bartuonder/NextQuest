"""Persistence helpers for a user's favourite titles."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.enums import SAMPLES_PER_CATEGORY, Category
from models import Favorite, User
from schemas.favorite import FavoriteCreate, TasteProfile


class FavoriteLimitError(ValueError):
    """Raised when a category already holds the maximum number of samples."""


class DuplicateFavoriteError(ValueError):
    """Raised when the same title is added twice to the same category."""


def list_favorites(db: Session, user: User) -> list[Favorite]:
    stmt = (
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.category, Favorite.id)
    )
    return list(db.scalars(stmt))


def add_favorite(db: Session, user: User, data: FavoriteCreate) -> Favorite:
    existing = list(
        db.scalars(
            select(Favorite).where(
                Favorite.user_id == user.id, Favorite.category == data.category
            )
        )
    )
    if any(item.title.casefold() == data.title.casefold() for item in existing):
        raise DuplicateFavoriteError(f"{data.title} is already in your list.")
    if len(existing) >= SAMPLES_PER_CATEGORY:
        raise FavoriteLimitError(
            f"You can keep at most {SAMPLES_PER_CATEGORY} {data.category.label} "
            "favourites. Remove one first."
        )

    favorite = Favorite(
        user_id=user.id, category=data.category, title=data.title, note=data.note
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def delete_favorite(db: Session, user: User, favorite_id: int) -> bool:
    favorite = db.get(Favorite, favorite_id)
    if favorite is None or favorite.user_id != user.id:
        return False
    db.delete(favorite)
    db.commit()
    return True


def replace_taste(db: Session, user: User, taste: TasteProfile) -> list[Favorite]:
    """Overwrite every favourite with the submitted questionnaire."""
    # Deleted one by one rather than in bulk so the identity map stays in sync and
    # the rows we insert next cannot collide with stale ones.
    for favorite in list_favorites(db, user):
        db.delete(favorite)
    db.flush()

    favorites = [
        Favorite(user_id=user.id, category=category, title=title)
        for category, title in taste.as_favorites()
    ]
    db.add_all(favorites)
    db.commit()
    return list_favorites(db, user)


def taste_from_favorites(favorites: list[Favorite]) -> TasteProfile:
    buckets: dict[Category, list[str]] = {category: [] for category in Category}
    for favorite in favorites:
        buckets[favorite.category].append(favorite.title)
    return TasteProfile(
        games=buckets[Category.GAME],
        movies=buckets[Category.MOVIE],
        books=buckets[Category.BOOK],
        tv_series=buckets[Category.TV_SERIES],
        animes=buckets[Category.ANIME],
    )
