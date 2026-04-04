from __future__ import annotations

import uuid
from decimal import Decimal

from app.schemas.base import APIModel


class ParticipantBalanceRead(APIModel):
    participant_id: uuid.UUID
    name: str
    color_hex: str | None
    is_active: bool
    is_owner: bool
    paid_total: Decimal
    owed_total: Decimal
    net_balance: Decimal


class SettlementRead(APIModel):
    from_participant_id: uuid.UUID
    from_name: str
    to_participant_id: uuid.UUID
    to_name: str
    amount: Decimal


class BalanceSnapshotRead(APIModel):
    total_spent: Decimal
    you_owe: Decimal
    you_are_owed: Decimal
    balances: list[ParticipantBalanceRead]
    settlements: list[SettlementRead]
