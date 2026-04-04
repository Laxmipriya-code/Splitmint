from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.db.models import Expense, ExpenseSplit, Group, Participant
from app.services.balances import balance_service
from app.services.ledger import expense_split_normalizer


def test_equal_split_rounding_is_deterministic() -> None:
    participant_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    splits = expense_split_normalizer.normalize(
        amount=Decimal("100.00"),
        participant_ids=participant_ids,
        split_mode="equal",
        split_values={},
    )

    assert [split.owed_amount for split in splits] == [
        Decimal("33.34"),
        Decimal("33.33"),
        Decimal("33.33"),
    ]


def test_custom_split_requires_exact_total() -> None:
    participant_ids = [uuid.uuid4(), uuid.uuid4()]
    try:
        expense_split_normalizer.normalize(
            amount=Decimal("50.00"),
            participant_ids=participant_ids,
            split_mode="custom",
            split_values={
                participant_ids[0]: Decimal("10.00"),
                participant_ids[1]: Decimal("39.99"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        assert "sum exactly" in str(exc)
    else:
        raise AssertionError("Expected custom split validation error")


def test_percentage_split_rounding_preserves_total() -> None:
    participant_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    splits = expense_split_normalizer.normalize(
        amount=Decimal("100.00"),
        participant_ids=participant_ids,
        split_mode="percentage",
        split_values={
            participant_ids[0]: Decimal("50.0000"),
            participant_ids[1]: Decimal("30.0000"),
            participant_ids[2]: Decimal("20.0000"),
        },
    )

    assert [split.owed_amount for split in splits] == [
        Decimal("50.00"),
        Decimal("30.00"),
        Decimal("20.00"),
    ]


def test_balance_service_generates_minimal_settlements() -> None:
    group = Group(name="Trip", owner_id=uuid.uuid4())
    owner = Participant(
        id=uuid.uuid4(),
        group_id=group.id,
        name="A",
        name_key="a",
        is_active=True,
        is_owner=True,
    )
    bob = Participant(
        id=uuid.uuid4(),
        group_id=group.id,
        name="B",
        name_key="b",
        is_active=True,
        is_owner=False,
    )
    charlie = Participant(
        id=uuid.uuid4(),
        group_id=group.id,
        name="C",
        name_key="c",
        is_active=True,
        is_owner=False,
    )
    group.participants = [owner, bob, charlie]
    group.expenses = [
        Expense(
            id=uuid.uuid4(),
            group_id=group.id,
            payer_id=owner.id,
            payer=owner,
            amount=Decimal("200.00"),
            description="Hotel",
            category="Travel",
            split_mode="custom",
            expense_date=date(2026, 4, 1),
            splits=[
                ExpenseSplit(
                    participant_id=bob.id,
                    participant=bob,
                    owed_amount=Decimal("100.00"),
                    position=0,
                ),
                ExpenseSplit(
                    participant_id=charlie.id,
                    participant=charlie,
                    owed_amount=Decimal("100.00"),
                    position=1,
                ),
            ],
        )
    ]

    snapshot = balance_service.build_snapshot(group)
    assert snapshot.settlements[0].from_name == "B"
    assert snapshot.settlements[0].to_name == "A"
    assert snapshot.settlements[0].amount == Decimal("100.00")
    assert snapshot.settlements[1].from_name == "C"
    assert snapshot.settlements[1].to_name == "A"
    assert snapshot.settlements[1].amount == Decimal("100.00")
