from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.enums import SAMPLES_PER_CATEGORY, Category


class FavoriteCreate(BaseModel):
    category: Category
    title: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("title", "note")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class FavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: Category
    title: str
    note: str | None = None
    created_at: datetime


class TasteProfile(BaseModel):
    """The full 3-per-category questionnaire submitted in one shot."""

    games: list[str] = Field(default_factory=list)
    movies: list[str] = Field(default_factory=list)
    books: list[str] = Field(default_factory=list)
    tv_series: list[str] = Field(default_factory=list)
    animes: list[str] = Field(default_factory=list)

    @field_validator("*", mode="before")
    @classmethod
    def _clean(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:SAMPLES_PER_CATEGORY]

    def as_favorites(self) -> list[tuple[Category, str]]:
        mapping = {
            Category.GAME: self.games,
            Category.MOVIE: self.movies,
            Category.BOOK: self.books,
            Category.TV_SERIES: self.tv_series,
            Category.ANIME: self.animes,
        }
        return [
            (category, title)
            for category, titles in mapping.items()
            for title in titles
        ]
