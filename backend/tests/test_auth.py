from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_and_login


def test_register_and_me(client: TestClient) -> None:
    tokens = register_and_login(client)

    me_response = client.get("/api/v1/auth/me", headers=auth_headers(tokens["access_token"]))
    assert me_response.status_code == 200
    payload = me_response.json()["data"]
    assert payload["email"] == "owner@example.com"
    assert payload["display_name"] == "Owner"


def test_login_invalid_credentials(client: TestClient) -> None:
    register_and_login(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_refresh_rotates_token_and_logout_revokes_it(client: TestClient) -> None:
    tokens = register_and_login(client)

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()["data"]["tokens"]
    assert refreshed["refresh_token"] != tokens["refresh_token"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers=auth_headers(refreshed["access_token"]),
        json={"refresh_token": refreshed["refresh_token"]},
    )
    assert logout_response.status_code == 200

    second_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refreshed["refresh_token"]},
    )
    assert second_refresh.status_code == 401
