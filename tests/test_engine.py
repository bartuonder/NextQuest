"""Unit tests for the parts of the engine that run without hitting OpenAI."""

from core.config import Settings
from core.enums import Category
from schemas.favorite import TasteProfile
from schemas.recommendation import LLMRecommendation, LLMRecommendationSet
from services.llm_engine import (
    MAX_TOP_UP_ROUNDS,
    LLMEngineError,
    RecommendationEngine,
    _deficits,
    _format_taste,
    _post_process,
)


def recommendation(category: Category, title: str, score: int = 80) -> LLMRecommendation:
    return LLMRecommendation(
        category=category, title=title, reason="Because. And also because.", match_score=score
    )


def test_format_taste_groups_titles_by_category():
    taste = TasteProfile(games=["Hollow Knight", "Celeste"], books=["Dune"])
    block = _format_taste(taste.as_favorites())
    assert "- Game: Hollow Knight, Celeste" in block
    assert "- Book: Dune" in block


def test_post_process_drops_echoes_duplicates_and_extras():
    kept = _post_process(
        [
            recommendation(Category.GAME, "Hollow Knight"),  # already owned
            recommendation(Category.GAME, "Celeste", 70),
            recommendation(Category.GAME, "celeste", 95),  # duplicate
            recommendation(Category.GAME, "Ori", 90),
            recommendation(Category.GAME, "Braid"),  # over per_category
            recommendation(Category.ANIME, "Monster"),  # category not requested
        ],
        wanted=[Category.GAME],
        per_category=2,
        already_owned={"hollow knight"},
    )
    assert [item.title for item in kept] == ["Ori", "Celeste"]  # sorted by score


def test_post_process_orders_categories_as_requested():
    kept = _post_process(
        [recommendation(Category.BOOK, "Piranesi"), recommendation(Category.GAME, "Ori")],
        wanted=[Category.GAME, Category.BOOK],
        per_category=3,
        already_owned=set(),
    )
    assert [item.category for item in kept] == [Category.GAME, Category.BOOK]


def test_deficits_counts_what_each_category_is_missing():
    kept = [recommendation(Category.GAME, "Ori"), recommendation(Category.BOOK, "Dune")]
    assert _deficits(kept, wanted=[Category.GAME, Category.BOOK], per_category=1) == {}
    assert _deficits(kept, wanted=[Category.GAME, Category.ANIME], per_category=3) == {
        Category.GAME: 2,
        Category.ANIME: 3,
    }


def stub_engine(monkeypatch, responses):
    """An engine whose chain replays `responses` and records each payload."""
    engine = RecommendationEngine(Settings(openai_api_key="sk-test", _env_file=None))
    payloads: list[dict] = []

    class Chain:
        def invoke(self, payload):
            payloads.append(payload)
            answer = responses[min(len(payloads) - 1, len(responses) - 1)]
            if isinstance(answer, Exception):
                raise answer
            return answer

    monkeypatch.setattr(engine, "_chain", Chain())
    return engine, payloads


def test_engine_uses_a_stubbed_chain(monkeypatch):
    engine, payloads = stub_engine(
        monkeypatch,
        [
            LLMRecommendationSet(
                summary="Moody stuff.",
                recommendations=[recommendation(Category.GAME, "Ori")],
            )
        ],
    )

    result = engine.generate(
        TasteProfile(games=["Hollow Knight"]), categories=[Category.GAME], per_category=1
    )
    assert result.summary == "Moody stuff."
    assert [item.title for item in result.recommendations] == ["Ori"]
    assert len(payloads) == 1  # nothing was missing, so no second call
    assert payloads[0]["categories"] == "Game"
    assert payloads[0]["mood"] == "none"
    assert payloads[0]["avoid"] == "nothing yet"


def test_engine_tops_up_categories_the_model_skipped(monkeypatch):
    engine, payloads = stub_engine(
        monkeypatch,
        [
            LLMRecommendationSet(
                summary="Moody stuff.",
                recommendations=[recommendation(Category.GAME, "Ori")],
            ),
            LLMRecommendationSet(
                summary="Second pass.",
                recommendations=[
                    recommendation(Category.GAME, "Celeste"),
                    recommendation(Category.BOOK, "Piranesi"),
                    recommendation(Category.BOOK, "Solaris"),
                ],
            ),
        ],
    )

    result = engine.generate(
        TasteProfile(games=["Hollow Knight"]),
        categories=[Category.GAME, Category.BOOK],
        per_category=2,
    )

    assert len(payloads) == 2  # everything was filled, so no third round
    assert payloads[1]["categories"] == "Game (1 more needed), Book (2 more needed)"
    assert "Ori" in payloads[1]["avoid"]
    assert {item.title for item in result.recommendations} == {
        "Ori",
        "Celeste",
        "Piranesi",
        "Solaris",
    }
    assert result.summary == "Moody stuff."  # the first pass owns the summary


def test_top_up_stops_once_a_round_adds_nothing(monkeypatch):
    """The model repeating itself means it is out of ideas, so stop asking."""
    engine, payloads = stub_engine(
        monkeypatch,
        [
            LLMRecommendationSet(
                summary="Moody stuff.",
                recommendations=[recommendation(Category.GAME, "Ori")],
            )
        ],
    )

    result = engine.generate(
        TasteProfile(games=["Hollow Knight"]), categories=[Category.GAME], per_category=5
    )
    assert len(payloads) == 2  # one first pass, one fruitless top-up
    assert [item.title for item in result.recommendations] == ["Ori"]


def test_top_up_rounds_are_bounded(monkeypatch):
    """Each round adds one title, so only the round cap can stop the loop."""
    titles = iter(["Celeste", "Ori", "Braid", "Gris", "Inside", "Limbo"])

    engine = RecommendationEngine(Settings(openai_api_key="sk-test", _env_file=None))
    payloads: list[dict] = []

    class Chain:
        def invoke(self, payload):
            payloads.append(payload)
            return LLMRecommendationSet(
                summary="Moody stuff.", recommendations=[recommendation(Category.GAME, next(titles))]
            )

    monkeypatch.setattr(engine, "_chain", Chain())

    result = engine.generate(
        TasteProfile(games=["Hollow Knight"]), categories=[Category.GAME], per_category=5
    )
    assert len(payloads) == 1 + MAX_TOP_UP_ROUNDS
    assert len(result.recommendations) == 1 + MAX_TOP_UP_ROUNDS


def test_a_failing_top_up_still_returns_the_first_pass(monkeypatch):
    engine, payloads = stub_engine(
        monkeypatch,
        [
            LLMRecommendationSet(
                summary="Moody stuff.",
                recommendations=[recommendation(Category.GAME, "Ori")],
            ),
            RuntimeError("upstream timeout"),
        ],
    )

    result = engine.generate(
        TasteProfile(games=["Hollow Knight"]), categories=[Category.GAME], per_category=3
    )
    assert len(payloads) == 2
    assert [item.title for item in result.recommendations] == ["Ori"]


def test_an_empty_first_pass_is_an_error(monkeypatch):
    engine, _ = stub_engine(
        monkeypatch,
        [LLMRecommendationSet(summary="Nothing.", recommendations=[]), RuntimeError("nope")],
    )

    try:
        engine.generate(TasteProfile(games=["Hollow Knight"]), per_category=1)
    except LLMEngineError as exc:
        assert "usable suggestion" in str(exc)
    else:
        raise AssertionError("expected LLMEngineError")
