from enum import StrEnum


class Category(StrEnum):
    """The five media types NextQuest collects taste samples for."""

    GAME = "game"
    MOVIE = "movie"
    BOOK = "book"
    TV_SERIES = "tv_series"
    ANIME = "anime"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS: dict[Category, str] = {
    Category.GAME: "Game",
    Category.MOVIE: "Movie",
    Category.BOOK: "Book",
    Category.TV_SERIES: "TV Series",
    Category.ANIME: "Anime",
}

#: Number of favourite titles a user provides per category.
SAMPLES_PER_CATEGORY = 3
