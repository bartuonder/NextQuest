import pytest

from core.config import Settings
from services.llm_engine import LLMNotConfiguredError, RecommendationEngine, get_engine
from tests.conftest import SAMPLE_TASTE


def test_generate_from_an_inline_taste_profile(auth_client, fake_engine):
    response = auth_client.post(
        "/api/recommendations",
        json={"taste": SAMPLE_TASTE, "mood": "rainy sunday", "per_category": 2},
    )
    assert response.status_code == 201

    batch = response.json()
    assert batch["model"] == "fake-model"
    assert batch["mood"] == "rainy sunday"
    assert len(batch["items"]) == 10  # five categories x two picks
    assert batch["source_favorites"]["game"] == SAMPLE_TASTE["games"]
    assert fake_engine.calls[0]["per_category"] == 2

    item = batch["items"][0]
    assert item["reason"] and item["tags"] and 0 <= item["match_score"] <= 100

    # save_favorites defaults to true, so the questionnaire is now persisted.
    assert auth_client.get("/api/favorites/taste").json() == SAMPLE_TASTE


def test_generate_falls_back_to_saved_favorites(auth_client):
    auth_client.put("/api/favorites/taste", json=SAMPLE_TASTE)

    response = auth_client.post("/api/recommendations", json={})
    assert response.status_code == 201
    assert len(response.json()["items"]) == 15


def test_generate_can_be_limited_to_some_categories(auth_client):
    response = auth_client.post(
        "/api/recommendations",
        json={"taste": SAMPLE_TASTE, "categories": ["book", "anime"], "per_category": 3},
    )
    assert response.status_code == 201
    assert {item["category"] for item in response.json()["items"]} == {"book", "anime"}


def test_generate_without_any_taste_is_a_bad_gateway(auth_client):
    response = auth_client.post("/api/recommendations", json={})
    assert response.status_code == 502
    assert "at least one favourite" in response.json()["detail"]


def test_save_favorites_false_leaves_the_profile_untouched(auth_client):
    auth_client.post(
        "/api/recommendations", json={"taste": SAMPLE_TASTE, "save_favorites": False}
    )
    taste = auth_client.get("/api/favorites/taste").json()
    assert all(titles == [] for titles in taste.values())


def test_history_is_listed_newest_first_and_scoped_to_the_owner(auth_client, client):
    first = auth_client.post("/api/recommendations", json={"taste": SAMPLE_TASTE}).json()
    second = auth_client.post("/api/recommendations", json={"taste": SAMPLE_TASTE}).json()

    history = auth_client.get("/api/recommendations").json()
    assert [batch["id"] for batch in history] == [second["id"], first["id"]]

    intruder = client.post(
        "/api/auth/register",
        json={"username": "mallory", "email": "m@example.com", "password": "supersecret1"},
    ).json()
    headers = {"Authorization": f"Bearer {intruder['access_token']}"}
    assert client.get("/api/recommendations", headers=headers).json() == []
    assert client.get(f"/api/recommendations/{first['id']}", headers=headers).status_code == 404


def test_fetch_and_delete_a_batch(auth_client):
    batch_id = auth_client.post("/api/recommendations", json={"taste": SAMPLE_TASTE}).json()["id"]

    assert auth_client.get(f"/api/recommendations/{batch_id}").json()["id"] == batch_id
    assert auth_client.delete(f"/api/recommendations/{batch_id}").status_code == 204
    assert auth_client.get(f"/api/recommendations/{batch_id}").status_code == 404
    assert auth_client.delete(f"/api/recommendations/{batch_id}").status_code == 404


def test_missing_api_key_is_reported_as_service_unavailable(auth_client):
    from main import app

    app.dependency_overrides[get_engine] = lambda: RecommendationEngine(
        Settings(openai_api_key=None, _env_file=None)
    )
    response = auth_client.post("/api/recommendations", json={"taste": SAMPLE_TASTE})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_engine_refuses_to_build_a_chain_without_a_key():
    from schemas.favorite import TasteProfile

    engine = RecommendationEngine(Settings(openai_api_key=None, _env_file=None))
    with pytest.raises(LLMNotConfiguredError):
        engine.generate(TasteProfile(games=["Hollow Knight"]))
