from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProductEvent
from tests.conftest import auth_headers, register_and_login


def test_metrics_endpoint_exposes_prometheus_counters(client: TestClient) -> None:
    health_response = client.get("/health")
    assert health_response.status_code == 200

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.text
    assert "splitmint_http_requests_total" in body
    assert 'path="/health"' in body
    assert "splitmint_http_request_duration_seconds_sum" in body
    assert "splitmint_http_errors_total" in body


def test_product_events_are_recorded_for_key_actions(
    client: TestClient,
    db_session: Session,
) -> None:
    tokens = register_and_login(client)
    headers = auth_headers(tokens["access_token"])

    group_response = client.post("/api/v1/groups", headers=headers, json={"name": "Observability"})
    assert group_response.status_code == 201, group_response.text
    group = group_response.json()["data"]

    participant_response = client.post(
        f"/api/v1/groups/{group['id']}/participants",
        headers=headers,
        json={"name": "Rahul"},
    )
    assert participant_response.status_code == 201, participant_response.text
    participant = participant_response.json()["data"]

    expense_response = client.post(
        "/api/v1/expenses",
        headers=headers,
        json={
            "group_id": group["id"],
            "amount": "50.00",
            "description": "Lunch",
            "date": str(date.today()),
            "payer_id": group["owner_participant_id"],
            "participants": [group["owner_participant_id"], participant["id"]],
            "split_mode": "equal",
            "splits": [],
        },
    )
    assert expense_response.status_code == 201, expense_response.text

    balances_response = client.get(f"/api/v1/groups/{group['id']}/balances", headers=headers)
    assert balances_response.status_code == 200

    ai_parse_response = client.post(
        "/api/v1/ai/parse-expense",
        headers=headers,
        json={
            "group_id": group["id"],
            "text": "I paid 500 for dinner with Rahul",
        },
    )
    assert ai_parse_response.status_code == 200

    ai_summary_response = client.post(
        f"/api/v1/ai/groups/{group['id']}/summary",
        headers=headers,
        json={"max_highlights": 3},
    )
    assert ai_summary_response.status_code == 200

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout_response.status_code == 200

    db_session.expire_all()
    event_names = set(
        db_session.execute(select(ProductEvent.event_name)).scalars().all()
    )
    assert {
        "auth.register",
        "group.create",
        "participant.create",
        "expense.create",
        "balance.snapshot",
        "ai.parse_expense",
        "ai.group_summary",
        "auth.logout",
    }.issubset(event_names)
