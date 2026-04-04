from __future__ import annotations

import uuid
from datetime import date as CalendarDate
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.base import APIModel

SplitMode = Literal["equal", "custom", "percentage"]


class ExpenseSplitValueInput(APIModel):
    participant_id: uuid.UUID
    value: Decimal = Field(gt=0)


class ExpenseUpsertRequest(APIModel):
    group_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    date: CalendarDate
    payer_id: uuid.UUID
    participants: list[uuid.UUID] = Field(min_length=1)
    split_mode: SplitMode
    splits: list[ExpenseSplitValueInput] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return " ".join(value.strip().split()) if value else None

    @model_validator(mode="after")
    def validate_splits_shape(self) -> ExpenseUpsertRequest:
        if len(set(self.participants)) != len(self.participants):
            raise ValueError("participants must be unique")

        if self.split_mode == "equal" and self.splits:
            raise ValueError("equal splits must not include explicit split values")

        if self.split_mode in {"custom", "percentage"}:
            if not self.splits:
                raise ValueError(f"{self.split_mode} split mode requires split values")
            split_ids = [item.participant_id for item in self.splits]
            if len(set(split_ids)) != len(split_ids):
                raise ValueError("split participants must be unique")
            if set(split_ids) != set(self.participants):
                raise ValueError("participants must match split participant ids")

        return self


class ExpenseSplitRead(APIModel):
    participant_id: uuid.UUID
    participant_name: str
    owed_amount: Decimal
    input_value: Decimal | None
    position: int


class ExpenseRead(APIModel):
    id: uuid.UUID
    group_id: uuid.UUID
    payer_id: uuid.UUID
    payer_name: str
    amount: Decimal
    description: str
    category: str | None
    split_mode: SplitMode
    date: CalendarDate
    splits: list[ExpenseSplitRead]
    created_at: datetime
    updated_at: datetime
    version: int


class ExpenseListRead(APIModel):
    items: list[ExpenseRead]
    total: int
    page: int
    size: int
