from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import auth_headers, register_and_login

# Load from env var first, then the backend .env-backed settings loader.
OPENAI_API_KEY = os.getenv("SPLITMINT_OPENAI_API_KEY") or get_settings().openai_api_key
if not OPENAI_API_KEY:
    raise RuntimeError(
        "SPLITMINT_OPENAI_API_KEY is required for real AI integration tests."
    )


@pytest.fixture()
def ai_enabled() -> None:
    os.environ["SPLITMINT_AI_ENABLED"] = "true"
    os.environ["SPLITMINT_OPENAI_API_KEY"] = OPENAI_API_KEY
    get_settings.cache_clear()
    try:
        yield
    finally:
        os.environ["SPLITMINT_AI_ENABLED"] = "false"
        get_settings.cache_clear()


def test_ai_parse_with_real_model(client: TestClient, ai_enabled: None) -> None:
    tokens = register_and_login(client)
    headers = auth_headers(tokens["access_token"])

    group_response = client.post("/api/v1/groups", headers=headers, json={"name": "AI Group"})
    assert group_response.status_code == 201
    group = group_response.json()["data"]

    participant_response = client.post(
        f"/api/v1/groups/{group['id']}/participants",
        headers=headers,
        json={"name": "Rahul"},
    )
    assert participant_response.status_code == 201

    response = client.post(
        "/api/v1/ai/parse-expense",
        headers=headers,
        json={
            "group_id": group["id"],
            "text": "I paid 1200 for dinner with Rahul",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["draft"]["description"]
    assert isinstance(payload["draft"]["needs_confirmation"], bool)


def test_ai_summary_with_real_model(client: TestClient, ai_enabled: None) -> None:
    tokens = register_and_login(client)
    headers = auth_headers(tokens["access_token"])

    group_response = client.post("/api/v1/groups", headers=headers, json={"name": "AI Summary"})
    assert group_response.status_code == 201
    group = group_response.json()["data"]

    response = client.post(
        f"/api/v1/ai/groups/{group['id']}/summary",
        headers=headers,
        json={"max_highlights": 3},
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["summary"]
    assert isinstance(payload["highlights"], list)
