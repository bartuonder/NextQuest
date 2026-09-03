from tests.conftest import SAMPLE_TASTE


def add(client, title, category="game", note=None):
    return client.post(
        "/api/favorites", json={"category": category, "title": title, "note": note}
    )


def test_add_and_list_favorites(auth_client):
    assert auth_client.get("/api/favorites").json() == []

    created = add(auth_client, "Hollow Knight", note="perfect movement")
    assert created.status_code == 201
    assert created.json()["title"] == "Hollow Knight"
    assert created.json()["note"] == "perfect movement"

    listed = auth_client.get("/api/favorites").json()
    assert [item["title"] for item in listed] == ["Hollow Knight"]


def test_duplicate_titles_are_rejected_case_insensitively(auth_client):
    add(auth_client, "Hollow Knight")
    assert add(auth_client, "hollow knight").status_code == 409


def test_the_same_title_may_live_in_two_categories(auth_client):
    assert add(auth_client, "Dune", category="movie").status_code == 201
    assert add(auth_client, "Dune", category="book").status_code == 201


def test_a_category_holds_at_most_three_titles(auth_client):
    for title in ("Hollow Knight", "Disco Elysium", "Outer Wilds"):
        assert add(auth_client, title).status_code == 201

    overflow = add(auth_client, "Celeste")
    assert overflow.status_code == 422
    assert "at most 3" in overflow.json()["detail"]


def test_delete_favorite(auth_client):
    favorite_id = add(auth_client, "Hollow Knight").json()["id"]

    assert auth_client.delete(f"/api/favorites/{favorite_id}").status_code == 204
    assert auth_client.get("/api/favorites").json() == []
    assert auth_client.delete(f"/api/favorites/{favorite_id}").status_code == 404


def test_a_user_cannot_touch_another_users_favorites(auth_client, client):
    favorite_id = add(auth_client, "Hollow Knight").json()["id"]

    intruder = client.post(
        "/api/auth/register",
        json={"username": "mallory", "email": "m@example.com", "password": "supersecret1"},
    ).json()
    headers = {"Authorization": f"Bearer {intruder['access_token']}"}

    assert client.delete(f"/api/favorites/{favorite_id}", headers=headers).status_code == 404
    assert client.get("/api/favorites", headers=headers).json() == []


def test_taste_questionnaire_replaces_everything(auth_client):
    add(auth_client, "Celeste")

    response = auth_client.put("/api/favorites/taste", json=SAMPLE_TASTE)
    assert response.status_code == 200
    assert len(response.json()) == 15
    assert "Celeste" not in [item["title"] for item in response.json()]

    taste = auth_client.get("/api/favorites/taste").json()
    assert taste == SAMPLE_TASTE


def test_taste_keeps_only_the_first_three_titles(auth_client):
    auth_client.put(
        "/api/favorites/taste",
        json={"games": ["A", "B", "C", "D", "E"], "movies": ["  ", ""]},
    )
    taste = auth_client.get("/api/favorites/taste").json()
    assert taste["games"] == ["A", "B", "C"]
    assert taste["movies"] == []
