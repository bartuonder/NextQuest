def register(client, **overrides):
    payload = {
        "username": "newcomer",
        "email": "newcomer@example.com",
        "password": "supersecret1",
    } | overrides
    return client.post("/api/auth/register", json=payload)


def test_health_and_meta(client):
    assert client.get("/health").json()["status"] == "ok"

    meta = client.get("/api/meta").json()
    assert meta["samples_per_category"] == 3
    assert [category["value"] for category in meta["categories"]] == [
        "game",
        "movie",
        "book",
        "tv_series",
        "anime",
    ]


def test_register_returns_a_usable_token(client):
    response = register(client)
    assert response.status_code == 201

    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "newcomer"
    assert "password" not in body["user"]

    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "newcomer@example.com"


def test_duplicate_username_and_email_are_rejected(client):
    assert register(client).status_code == 201
    assert register(client, email="other@example.com").status_code == 409
    assert register(client, username="other").status_code == 409


def test_weak_password_is_rejected(client):
    assert register(client, password="short").status_code == 422


def test_login_accepts_username_or_email(client):
    register(client)

    for handle in ("newcomer", "newcomer@example.com"):
        response = client.post(
            "/api/auth/login", json={"username": handle, "password": "supersecret1"}
        )
        assert response.status_code == 200, handle
        assert response.json()["access_token"]


def test_login_rejects_a_wrong_password(client):
    register(client)
    response = client.post(
        "/api/auth/login", json={"username": "newcomer", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_oauth2_token_endpoint_works_for_swagger(client):
    register(client)
    response = client.post(
        "/api/auth/token",
        data={"username": "newcomer", "password": "supersecret1"},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_protected_routes_need_a_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/favorites").status_code == 401

    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401
