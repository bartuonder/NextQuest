"""LangChain powered recommendation engine.

The engine turns a user's taste samples (three titles per category) into
structured suggestions. `ChatOpenAI.with_structured_output` makes the model
answer with a validated `LLMRecommendationSet` instead of free text, so the API
layer never has to parse prose.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from core.config import Settings, get_settings
from core.enums import Category
from schemas.favorite import TasteProfile
from schemas.recommendation import LLMRecommendation, LLMRecommendationSet

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are NextQuest, a recommendation curator for games, movies, \
books, TV series and anime.

The user gives you up to three titles they already love per category. Use them to \
infer their taste - tone, pacing, themes, era, art style - and then suggest new \
works they have most likely not seen yet.

Rules you must follow:
- Suggest exactly {per_category} titles for each requested category, no more and no less.
- Never suggest a title the user already listed, and never repeat a title twice.
- Prefer well-known, actually existing works; do not invent titles.
- Every reason must be two sentences and must name at least one title the user listed.
- match_score is your confidence from 0 to 100.
- Write in the same language the user's titles and mood are written in; default to English.
"""

HUMAN_PROMPT = """Requested categories: {categories}
Suggestions per category: {per_category}

Titles the user already loves:
{taste_block}

Extra mood or constraint from the user: {mood}

Titles you must not suggest: {avoid}

Return a summary of their taste plus the suggestions."""


class LLMEngineError(RuntimeError):
    """Raised when the recommendation engine cannot produce a result."""


class LLMNotConfiguredError(LLMEngineError):
    """Raised when no OpenAI API key is available."""


class RecommendationEngine:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._chain = None

    @property
    def model_name(self) -> str:
        return self.settings.openai_model

    def _build_chain(self):
        if not self.settings.llm_enabled:
            raise LLMNotConfiguredError(
                "OPENAI_API_KEY is not set. Add it to your .env file to enable "
                "recommendations."
            )
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise LLMEngineError(
                "langchain-openai is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self._enable_tracing()
        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT), ("human", HUMAN_PROMPT)]
        )
        llm = ChatOpenAI(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            timeout=self.settings.openai_timeout,
            api_key=self.settings.openai_api_key,
            max_retries=2,
        )
        return prompt | llm.with_structured_output(LLMRecommendationSet)

    def _enable_tracing(self) -> None:
        """LangSmith is configured through environment variables, so opt in here."""
        if not self.settings.tracing_enabled:
            return
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_API_KEY", self.settings.langchain_api_key or "")
        os.environ.setdefault("LANGSMITH_PROJECT", self.settings.langchain_project)
        logger.info("LangSmith tracing enabled for project %r", self.settings.langchain_project)

    @property
    def chain(self):
        if self._chain is None:
            self._chain = self._build_chain()
        return self._chain

    def generate(
        self,
        taste: TasteProfile,
        categories: list[Category] | None = None,
        per_category: int = 3,
        mood: str | None = None,
    ) -> LLMRecommendationSet:
        favorites = taste.as_favorites()
        if not favorites:
            raise LLMEngineError(
                "Add at least one favourite title before asking for recommendations."
            )

        wanted = list(categories or list(Category))
        owned = {title.casefold() for _, title in favorites}
        taste_block = _format_taste(favorites)

        result = self._invoke(
            categories=wanted, per_category=per_category, taste_block=taste_block, mood=mood
        )
        kept = _post_process(
            result.recommendations,
            wanted=wanted,
            per_category=per_category,
            already_owned=owned,
        )

        # Models routinely return fewer titles than asked for, so one extra pass
        # fills the gaps instead of handing the user a half-empty answer.
        short = _underfilled(kept, wanted=wanted, per_category=per_category)
        if short:
            logger.info(
                "Topping up %s", ", ".join(category.label for category in short)
            )
            kept = self._top_up(
                kept,
                short=short,
                wanted=wanted,
                per_category=per_category,
                taste_block=taste_block,
                mood=mood,
                owned=owned,
            )

        if not kept:
            raise LLMEngineError("The model did not return any usable suggestion.")
        result.recommendations = kept
        return result

    def _top_up(
        self,
        kept: list[LLMRecommendation],
        *,
        short: list[Category],
        wanted: list[Category],
        per_category: int,
        taste_block: str,
        mood: str | None,
        owned: set[str],
    ) -> list[LLMRecommendation]:
        """Ask once more for the categories that came back light. Best effort only."""
        try:
            extra = self._invoke(
                categories=short,
                per_category=per_category,
                taste_block=taste_block,
                mood=mood,
                avoid=[item.title for item in kept],
            )
        except LLMEngineError:
            logger.warning("Top-up pass failed; returning the first-pass suggestions")
            return kept

        return _post_process(
            kept + extra.recommendations,
            wanted=wanted,
            per_category=per_category,
            already_owned=owned,
        )

    def _invoke(
        self,
        *,
        categories: list[Category],
        per_category: int,
        taste_block: str,
        mood: str | None,
        avoid: list[str] | None = None,
    ) -> LLMRecommendationSet:
        payload = {
            "categories": ", ".join(category.label for category in categories),
            "per_category": per_category,
            "taste_block": taste_block,
            "mood": mood or "none",
            "avoid": ", ".join(avoid) if avoid else "nothing yet",
        }

        try:
            result = self.chain.invoke(payload)
        except LLMEngineError:
            raise
        except Exception as exc:  # noqa: BLE001 - surfaced as a 502 by the API layer
            logger.exception("LLM call failed")
            raise LLMEngineError(f"The recommendation model failed: {exc}") from exc

        if not isinstance(result, LLMRecommendationSet):
            raise LLMEngineError("The model returned an unexpected response shape.")
        return result


def _format_taste(favorites: list[tuple[Category, str]]) -> str:
    grouped: dict[Category, list[str]] = {}
    for category, title in favorites:
        grouped.setdefault(category, []).append(title)
    return "\n".join(
        f"- {category.label}: {', '.join(titles)}" for category, titles in grouped.items()
    )


def _underfilled(
    recommendations: list[LLMRecommendation],
    *,
    wanted: list[Category],
    per_category: int,
) -> list[Category]:
    """Categories that received fewer suggestions than the user asked for."""
    counts: dict[Category, int] = {}
    for item in recommendations:
        counts[item.category] = counts.get(item.category, 0) + 1
    return [category for category in wanted if counts.get(category, 0) < per_category]


def _post_process(
    recommendations: list[LLMRecommendation],
    *,
    wanted: list[Category],
    per_category: int,
    already_owned: set[str],
) -> list[LLMRecommendation]:
    """Drop echoes of the user's own titles, duplicates and unrequested categories."""
    seen: set[str] = set()
    counts: dict[Category, int] = {}
    kept: list[LLMRecommendation] = []

    for item in recommendations:
        key = item.title.casefold()
        if item.category not in wanted or key in already_owned or key in seen:
            continue
        if counts.get(item.category, 0) >= per_category:
            continue
        seen.add(key)
        counts[item.category] = counts.get(item.category, 0) + 1
        kept.append(item)

    kept.sort(key=lambda item: (wanted.index(item.category), -item.match_score))
    return kept


@lru_cache
def get_engine() -> RecommendationEngine:
    return RecommendationEngine()
