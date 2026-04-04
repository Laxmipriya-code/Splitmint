from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Expense, Group, Participant
from tests.conftest import auth_headers, register_and_login


def _create_group(client: TestClient, access_token: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/groups",
        headers=auth_headers(access_token),
        json={"name": "Weekend Trip"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_group_creation_limit_and_participant_updates(client: TestClient) -> None:
    tokens = register_and_login(client)
    group = _create_group(client, tokens["access_token"])
    group_id = group["id"]

    names = ["Rahul", "Ankit", "Neha"]
    participant_ids = []
    for name in names:
        response = client.post(
            f"/api/v1/groups/{group_id}/participants",
            headers=auth_headers(tokens["access_token"]),
            json={"name": name},
        )
        assert response.status_code == 201, response.text
        participant_ids.append(response.json()["data"]["id"])

    over_limit = client.post(
        f"/api/v1/groups/{group_id}/participants",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Fifth"},
    )
    assert over_limit.status_code == 400

    rename = client.put(
        f"/api/v1/participants/{participant_ids[0]}",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Rahul Kumar", "color_hex": "#123456"},
    )
    assert rename.status_code == 200
    assert rename.json()["data"]["name"] == "Rahul Kumar"


def test_participant_with_history_becomes_inactive_and_group_delete_cascades(
    client: TestClient,
    db_session: Session,
) -> None:
    tokens = register_and_login(client)
    group = _create_group(client, tokens["access_token"])
    group_id = group["id"]
    owner_id = group["owner_participant_id"]

    participant_response = client.post(
        f"/api/v1/groups/{group_id}/participants",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Rahul"},
    )
    participant_id = participant_response.json()["data"]["id"]

    expense_response = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group_id,
            "amount": "30.00",
            "description": "Lunch",
            "date": "2026-04-01",
            "payer_id": owner_id,
            "participants": [owner_id, participant_id],
            "split_mode": "equal",
            "splits": [],
        },
    )
    assert expense_response.status_code == 201, expense_response.text

    delete_participant = client.delete(
        f"/api/v1/participants/{participant_id}",
        headers=auth_headers(tokens["access_token"]),
    )
    assert delete_participant.status_code == 204

    db_session.expire_all()
    stored_participant = db_session.get(Participant, uuid.UUID(participant_id))
    assert stored_participant is not None
    assert stored_participant.is_active is False

    delete_group = client.delete(
        f"/api/v1/groups/{group_id}",
        headers=auth_headers(tokens["access_token"]),
    )
    assert delete_group.status_code == 204

    db_session.expire_all()
    assert db_session.get(Group, uuid.UUID(group_id)) is None
    assert db_session.query(Participant).count() == 0
    assert db_session.query(Expense).count() == 0
