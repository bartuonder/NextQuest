from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core.enums import Category
from schemas.favorite import TasteProfile


class RecommendationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: Category
    title: str
    year: int | None = None
    reason: str
    match_score: int = 0
    tags: list[str] = Field(default_factory=list)


class RecommendationBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str
    summary: str | None = None
    mood: str | None = None
    source_favorites: dict[str, list[str]] = Field(default_factory=dict)
    created_at: datetime
    items: list[RecommendationItemRead] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    """Optional inline taste profile; falls back to the user's saved favourites."""

    taste: TasteProfile | None = None
    mood: str | None = Field(default=None, max_length=200)
    categories: list[Category] | None = None
    per_category: int = Field(default=3, ge=1, le=5)
    save_favorites: bool = True


# --- Structures the LLM is asked to fill in --------------------------------


class LLMRecommendation(BaseModel):
    """One suggestion produced by the model."""

    category: Category = Field(description="Which media type this suggestion belongs to")
    title: str = Field(description="Official title of the work")
    year: int | None = Field(default=None, description="Release year, if known")
    reason: str = Field(
        description="Two sentences explaining why this fits the user's samples, "
        "naming at least one of the titles they listed"
    )
    match_score: int = Field(
        default=80, ge=0, le=100, description="Confidence that the user will enjoy it"
    )
    tags: list[str] = Field(
        default_factory=list, description="Three short genre or vibe tags"
    )


class LLMRecommendationSet(BaseModel):
    """Full structured answer returned by the LangChain chain."""

    summary: str = Field(
        description="One paragraph describing the user's taste in second person"
    )
    recommendations: list[LLMRecommendation] = Field(
        default_factory=list, description="All suggestions across the requested categories"
    )
