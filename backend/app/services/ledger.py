from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.core.errors import BadRequestError
from app.utils.money import (
    ZERO,
    allocate_rounded_amounts,
    ensure_exact_total,
    quantize_money,
    quantize_percentage,
)

SplitMode = Literal["equal", "custom", "percentage"]


@dataclass(slots=True)
class NormalizedSplitLine:
    participant_id: uuid.UUID
    owed_amount: Decimal
    input_value: Decimal | None
    position: int


class ExpenseSplitNormalizer:
    def normalize(
        self,
        *,
        amount: Decimal,
        participant_ids: list[uuid.UUID],
        split_mode: SplitMode,
        split_values: dict[uuid.UUID, Decimal],
    ) -> list[NormalizedSplitLine]:
        if not participant_ids:
            raise BadRequestError("At least one participant is required")

        amount = quantize_money(amount)

        if split_mode == "equal":
            raw_amounts = [amount / len(participant_ids) for _ in participant_ids]
            rounded_amounts = allocate_rounded_amounts(raw_amounts)
            return [
                NormalizedSplitLine(
                    participant_id=participant_id,
                    owed_amount=rounded_amounts[index],
                    input_value=None,
                    position=index,
                )
                for index, participant_id in enumerate(participant_ids)
            ]

        if split_mode == "custom":
            money_values = [
                quantize_money(split_values[participant_id]) for participant_id in participant_ids
            ]
            ensure_exact_total(money_values, amount, field_name="custom split amounts")
            return [
                NormalizedSplitLine(
                    participant_id=participant_id,
                    owed_amount=money_values[index],
                    input_value=money_values[index],
                    position=index,
                )
                for index, participant_id in enumerate(participant_ids)
            ]

        if split_mode == "percentage":
            percentages = [
                quantize_percentage(split_values[participant_id])
                for participant_id in participant_ids
            ]
            total_percentage = sum(percentages, ZERO).quantize(Decimal("0.0001"))
            if total_percentage != Decimal("100.0000"):
                raise BadRequestError(
                    "Percentage splits must sum exactly to 100.0000",
                    details={"actual_percentage_total": str(total_percentage)},
                )
            raw_amounts = [(amount * percentage) / Decimal("100") for percentage in percentages]
            rounded_amounts = allocate_rounded_amounts(raw_amounts)
            return [
                NormalizedSplitLine(
                    participant_id=participant_id,
                    owed_amount=rounded_amounts[index],
                    input_value=percentages[index],
                    position=index,
                )
                for index, participant_id in enumerate(participant_ids)
            ]

        raise BadRequestError("Unsupported split mode", details={"split_mode": split_mode})


expense_split_normalizer = ExpenseSplitNormalizer()
