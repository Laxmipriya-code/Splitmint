from __future__ import annotations

import uuid
from datetime import date as CalendarDate
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.schemas.base import APIModel


class MintSenseParseRequest(APIModel):
    text: str = Field(min_length=3, max_length=2000)
    group_id: uuid.UUID | None = None


class MintSenseSplitDraft(APIModel):
    participant_name: str
    value: Decimal


class MintSenseExpenseDraft(APIModel):
    description: str | None = None
    amount: Decimal | None = None
    category: str | None = None
    date: CalendarDate | None = None
    payer_name: str | None = None
    participant_names: list[str] = Field(default_factory=list)
    split_mode: Literal["equal", "custom", "percentage"] | None = None
    splits: list[MintSenseSplitDraft] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    needs_confirmation: bool = True


class MintSenseResolvedParty(APIModel):
    participant_id: uuid.UUID
    participant_name: str


class MintSenseParseResponse(APIModel):
    draft: MintSenseExpenseDraft
    resolved_payer: MintSenseResolvedParty | None = None
    resolved_participants: list[MintSenseResolvedParty] = Field(default_factory=list)
    validation_issues: list[str] = Field(default_factory=list)


class MintSenseGroupSummaryRequest(APIModel):
    max_highlights: int = Field(default=3, ge=1, le=10)


class MintSenseGroupSummaryRead(APIModel):
    summary: str
    highlights: list[str]
