from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_and_login


def _bootstrap_group(
    client: TestClient,
) -> tuple[dict[str, str], dict[str, object], dict[str, str]]:
    tokens = register_and_login(client)
    group_response = client.post(
        "/api/v1/groups",
        headers=auth_headers(tokens["access_token"]),
        json={"name": "Goa Trip"},
    )
    group = group_response.json()["data"]
    owner_id = group["owner_participant_id"]

    participants = {"owner": owner_id}
    for name in ["Rahul", "Ankit"]:
        response = client.post(
            f"/api/v1/groups/{group['id']}/participants",
            headers=auth_headers(tokens["access_token"]),
            json={"name": name},
        )
        participants[name.lower()] = response.json()["data"]["id"]

    return tokens, group, participants


def test_equal_split_balances_and_delete_recompute(client: TestClient) -> None:
    tokens, group, participants = _bootstrap_group(client)

    create_expense = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "100.00",
            "description": "Dinner",
            "date": "2026-04-01",
            "payer_id": participants["owner"],
            "participants": [
                participants["owner"],
                participants["rahul"],
                participants["ankit"],
            ],
            "split_mode": "equal",
            "splits": [],
        },
    )
    assert create_expense.status_code == 201, create_expense.text
    expense = create_expense.json()["data"]
    assert [split["owed_amount"] for split in expense["splits"]] == ["33.34", "33.33", "33.33"]

    balances = client.get(
        f"/api/v1/groups/{group['id']}/balances",
        headers=auth_headers(tokens["access_token"]),
    )
    assert balances.status_code == 200
    payload = balances.json()["data"]
    owner_balance = next(item for item in payload["balances"] if item["is_owner"])
    assert Decimal(owner_balance["net_balance"]) == Decimal("66.66")
    assert payload["settlements"][0]["amount"] == "33.33"
    assert payload["settlements"][1]["amount"] == "33.33"

    delete_expense = client.delete(
        f"/api/v1/expenses/{expense['id']}",
        headers=auth_headers(tokens["access_token"]),
    )
    assert delete_expense.status_code == 204

    zero_balances = client.get(
        f"/api/v1/groups/{group['id']}/balances",
        headers=auth_headers(tokens["access_token"]),
    )
    assert zero_balances.json()["data"]["total_spent"] == "0.00"
    assert zero_balances.json()["data"]["settlements"] == []


def test_custom_and_percentage_splits_and_filters(client: TestClient) -> None:
    tokens, group, participants = _bootstrap_group(client)

    custom_response = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "90.00",
            "description": "Cab ride",
            "date": "2026-04-01",
            "payer_id": participants["rahul"],
            "participants": [participants["owner"], participants["rahul"]],
            "split_mode": "custom",
            "splits": [
                {"participant_id": participants["owner"], "value": "50.00"},
                {"participant_id": participants["rahul"], "value": "40.00"},
            ],
        },
    )
    assert custom_response.status_code == 201, custom_response.text

    invalid_custom = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "90.00",
            "description": "Broken split",
            "date": "2026-04-01",
            "payer_id": participants["rahul"],
            "participants": [participants["owner"], participants["rahul"]],
            "split_mode": "custom",
            "splits": [
                {"participant_id": participants["owner"], "value": "50.00"},
                {"participant_id": participants["rahul"], "value": "39.00"},
            ],
        },
    )
    assert invalid_custom.status_code == 400

    percentage_response = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "100.00",
            "description": "Boat tickets",
            "date": "2026-04-02",
            "payer_id": participants["owner"],
            "participants": [
                participants["owner"],
                participants["rahul"],
                participants["ankit"],
            ],
            "split_mode": "percentage",
            "splits": [
                {"participant_id": participants["owner"], "value": "50.0000"},
                {"participant_id": participants["rahul"], "value": "30.0000"},
                {"participant_id": participants["ankit"], "value": "20.0000"},
            ],
        },
    )
    assert percentage_response.status_code == 201, percentage_response.text

    invalid_percentage = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "100.00",
            "description": "Invalid percentages",
            "date": "2026-04-02",
            "payer_id": participants["owner"],
            "participants": [
                participants["owner"],
                participants["rahul"],
                participants["ankit"],
            ],
            "split_mode": "percentage",
            "splits": [
                {"participant_id": participants["owner"], "value": "50.0000"},
                {"participant_id": participants["rahul"], "value": "30.0000"},
                {"participant_id": participants["ankit"], "value": "10.0000"},
            ],
        },
    )
    assert invalid_percentage.status_code == 400

    filtered = client.get(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        params={
            "group_id": group["id"],
            "search": "boat",
            "date_from": "2026-04-02",
            "min_amount": "90.00",
        },
    )
    assert filtered.status_code == 200
    data = filtered.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["description"] == "Boat tickets"


def test_expense_update_recalculates_payer_balance(client: TestClient) -> None:
    tokens, group, participants = _bootstrap_group(client)

    create_response = client.post(
        "/api/v1/expenses",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "60.00",
            "description": "Breakfast",
            "date": "2026-04-01",
            "payer_id": participants["owner"],
            "participants": [participants["owner"], participants["rahul"]],
            "split_mode": "equal",
            "splits": [],
        },
    )
    expense = create_response.json()["data"]

    update_response = client.put(
        f"/api/v1/expenses/{expense['id']}",
        headers=auth_headers(tokens["access_token"]),
        json={
            "group_id": group["id"],
            "amount": "60.00",
            "description": "Breakfast",
            "date": "2026-04-01",
            "payer_id": participants["rahul"],
            "participants": [participants["owner"], participants["rahul"]],
            "split_mode": "equal",
            "splits": [],
        },
    )
    assert update_response.status_code == 200, update_response.text

    balances = client.get(
        f"/api/v1/groups/{group['id']}/balances",
        headers=auth_headers(tokens["access_token"]),
    )
    owner_balance = next(item for item in balances.json()["data"]["balances"] if item["is_owner"])
    rahul_balance = next(
        item for item in balances.json()["data"]["balances"] if item["name"] == "Rahul"
    )
    assert owner_balance["net_balance"] == "-30.00"
    assert rahul_balance["net_balance"] == "30.00"
