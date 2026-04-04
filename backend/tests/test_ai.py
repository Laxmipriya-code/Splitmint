from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_and_login


def test_ai_parse_with_group_context_resolves_names(client: TestClient) -> None:
    tokens = register_and_login(client)
    group_response = client.post(
        "/api/v1/groups",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Dinner Club"},
    )
    group = group_response.json()["data"]

    for name in ["Rahul", "Ankit"]:
        client.post(
            f"/api/v1/groups/{group['id']}/participants",
            headers=auth_headers(tokens["access_token"]),
            json={"name": name},
        )

    response = client.post(
        "/api/v1/ai/parse-expense",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "text": "I paid 1200 for dinner with Rahul and Ankit",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["draft"]["amount"] == "1200.00"
    assert payload["draft"]["category"] == "Food & Dining"
    assert payload["draft"]["payer_name"] == "Owner"
    assert payload["draft"]["needs_confirmation"] is False
    assert len(payload["resolved_participants"]) == 2


def test_ai_parse_handles_ambiguous_input_safely(client: TestClient) -> None:
    tokens = register_and_login(client)

    response = client.post(
        "/api/v1/ai/parse-expense",
        headers=auth_headers(tokens["access_token"]),
        json={"text": "something happened maybe split it somehow"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["draft"]["needs_confirmation"] is True
    assert payload["validation_issues"]
