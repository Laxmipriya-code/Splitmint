from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator

from app.schemas.balance import BalanceSnapshotRead
from app.schemas.base import APIModel
from app.schemas.participant import ParticipantRead


class GroupCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class GroupUpdateRequest(APIModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class GroupListItemRead(APIModel):
    id: uuid.UUID
    name: str
    active_participant_count: int
    total_spent: Decimal
    you_owe: Decimal
    you_are_owed: Decimal
    created_at: datetime
    updated_at: datetime
    version: int


class GroupRead(APIModel):
    id: uuid.UUID
    name: str
    owner_participant_id: uuid.UUID
    participants: list[ParticipantRead]
    summary: BalanceSnapshotRead
    created_at: datetime
    updated_at: datetime
    version: int
