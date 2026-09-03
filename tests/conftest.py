"""Shared fixtures.

The environment is rewritten *before* the application modules are imported so
`core.config.Settings` binds to a throwaway SQLite file instead of the developer's
real database or OpenAI key.
"""

import os
import tempfile
from pathlib import Path

DB_PATH = Path(tempfile.gettempdir()) / "nextquest-test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("OPENAI_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.deps import get_current_user  # noqa: E402,F401  (imported for override keys)
from core.database import Base, engine  # noqa: E402
from core.enums import Category  # noqa: E402
from main import app  # noqa: E402
from schemas.recommendation import (  # noqa: E402
    LLMRecommendation,
    LLMRecommendationSet,
)
from services.llm_engine import get_engine  # noqa: E402


class FakeEngine:
    """Deterministic stand-in for the LangChain chain."""

    model_name = "fake-model"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, taste, categories=None, per_category=3, mood=None):
        self.calls.append(
            {"taste": taste, "categories": categories, "per_category": per_category, "mood": mood}
        )
        wanted = list(categories or list(Category))
        return LLMRecommendationSet(
            summary="You like moody, character-driven stories.",
            recommendations=[
                LLMRecommendation(
                    category=category,
                    title=f"{category.label} pick {index + 1}",
                    year=2020 + index,
                    reason="It matches your samples. You will probably enjoy it.",
                    match_score=90 - index,
                    tags=["moody", "slow-burn"],
                )
                for category in wanted
                for index in range(per_category)
            ],
        )


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def fake_engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def client(fake_engine: FakeEngine):
    app.dependency_overrides[get_engine] = lambda: fake_engine
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client: TestClient):
    """A client whose Authorization header is already set for a fresh account."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "bartu",
            "email": "bartu@example.com",
            "password": "supersecret1",
            "full_name": "Bartu Önder",
        },
    )
    assert response.status_code == 201, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


SAMPLE_TASTE = {
    "games": ["Hollow Knight", "Disco Elysium", "Outer Wilds"],
    "movies": ["Arrival", "Blade Runner 2049", "Prisoners"],
    "books": ["Dune", "Piranesi", "The Road"],
    "tv_series": ["Dark", "Severance", "True Detective"],
    "animes": ["Steins;Gate", "Monster", "Vinland Saga"],
}
