from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.errors import BadRequestError

CENT = Decimal("0.01")
PERCENT_QUANT = Decimal("0.0001")
ZERO = Decimal("0.00")


def to_decimal(value: Decimal | int | str | float) -> Decimal:
    return Decimal(str(value))


def quantize_money(value: Decimal | int | str | float) -> Decimal:
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def quantize_percentage(value: Decimal | int | str | float) -> Decimal:
    return to_decimal(value).quantize(PERCENT_QUANT, rounding=ROUND_HALF_UP)


def ensure_money_precision(value: Decimal | int | str | float, *, field_name: str) -> Decimal:
    decimal_value = to_decimal(value)
    quantized = quantize_money(decimal_value)
    if decimal_value != quantized:
        raise BadRequestError(
            f"{field_name} must have at most 2 decimal places",
            details={field_name: str(decimal_value)},
        )
    return quantized


def ensure_percentage_precision(value: Decimal | int | str | float, *, field_name: str) -> Decimal:
    decimal_value = to_decimal(value)
    quantized = quantize_percentage(decimal_value)
    if decimal_value != quantized:
        raise BadRequestError(
            f"{field_name} must have at most 4 decimal places",
            details={field_name: str(decimal_value)},
        )
    return quantized


def normalize_name_key(name: str) -> str:
    return " ".join(name.strip().lower().split())


def validate_positive_amount(
    value: Decimal | int | str | float, *, field_name: str = "amount"
) -> Decimal:
    amount = quantize_money(value)
    if amount <= ZERO:
        raise BadRequestError(
            f"{field_name} must be greater than zero", details={field_name: str(amount)}
        )
    return amount


def sum_money(values: Iterable[Decimal]) -> Decimal:
    total = ZERO
    for value in values:
        total += quantize_money(value)
    return quantize_money(total)


@dataclass(slots=True)
class AllocationCandidate:
    index: int
    raw_amount: Decimal
    rounded_amount: Decimal

    @property
    def delta(self) -> Decimal:
        return self.raw_amount - self.rounded_amount


def allocate_rounded_amounts(raw_amounts: Sequence[Decimal]) -> list[Decimal]:
    rounded = [quantize_money(amount) for amount in raw_amounts]
    total_raw = quantize_money(sum(raw_amounts, Decimal("0")))
    total_rounded = quantize_money(sum(rounded, Decimal("0")))
    difference = total_raw - total_rounded

    if difference == ZERO:
        return rounded

    candidates = [
        AllocationCandidate(index=i, raw_amount=raw_amounts[i], rounded_amount=rounded[i])
        for i in range(len(raw_amounts))
    ]

    step = CENT if difference > ZERO else -CENT
    adjustments = int(abs(difference / CENT))

    if difference > ZERO:
        ordered = sorted(candidates, key=lambda item: (item.delta, -item.index), reverse=True)
    else:
        ordered = sorted(candidates, key=lambda item: (item.delta, item.index))

    if not ordered:
        raise BadRequestError("Unable to allocate rounded amounts")

    for i in range(adjustments):
        target = ordered[i % len(ordered)]
        rounded[target.index] = quantize_money(rounded[target.index] + step)

    return rounded


def ensure_exact_total(
    values: Sequence[Decimal], expected_total: Decimal, *, field_name: str
) -> None:
    actual = quantize_money(sum(values, Decimal("0")))
    expected = quantize_money(expected_total)
    if actual != expected:
        raise BadRequestError(
            f"{field_name} must sum exactly to {expected}",
            details={"expected_total": str(expected), "actual_total": str(actual)},
        )
