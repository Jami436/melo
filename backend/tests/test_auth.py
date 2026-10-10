"""Tests for the /auth endpoints."""

from app.core.security import create_access_token


def signup_payload(**overrides) -> dict:
    data = {
        "email": "alice@example.com",
        "username": "alice",
        "password": "supersecret",
    }
    data.update(overrides)
    return data


def register(client, **overrides) -> None:
    response = client.post("/auth/signup", json=signup_payload(**overrides))
    assert response.status_code == 201, response.text


def login(client, email="alice@example.com", password="supersecret"):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------- signup ----


def test_signup_creates_user_without_leaking_password(client):
    response = client.post("/auth/signup", json=signup_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert isinstance(body["id"], int)
    assert "created_at" in body
    # The hash must never appear in any response.
    assert "hashed_password" not in body
    assert "password" not in body


def test_signup_rejects_duplicate_email(client):
    register(client)
    response = client.post(
        "/auth/signup", json=signup_payload(username="someone-else")
    )

    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower()


def test_signup_rejects_duplicate_username(client):
    register(client)
    response = client.post(
        "/auth/signup", json=signup_payload(email="other@example.com")
    )

    assert response.status_code == 409
    assert "username" in response.json()["detail"].lower()


# ----------------------------------------------------------------- login ----


def test_login_success_returns_token(client):
    register(client)
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_login_wrong_password_is_unauthorized(client):
    register(client)
    response = login(client, password="wrong-password")

    assert response.status_code == 401


def test_login_unknown_email_is_unauthorized(client):
    response = login(client, email="nobody@example.com")

    assert response.status_code == 401


# ------------------------------------------------------------------ /me ----


def test_me_without_token_is_unauthorized(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token_returns_user(client):
    register(client)
    token = login(client).json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert "hashed_password" not in body


def test_me_with_invalid_token_is_unauthorized(client):
    response = client.get(
        "/auth/me", headers={"Authorization": "Bearer not.a.valid.token"}
    )

    assert response.status_code == 401


def test_me_with_expired_token_is_unauthorized(client):
    register(client)
    # A token that expired one minute ago.
    expired = create_access_token(subject=1, expires_minutes=-1)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401
