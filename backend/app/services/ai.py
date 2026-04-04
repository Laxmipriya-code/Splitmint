from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.ai import (
    MintSenseExpenseDraft,
    MintSenseGroupSummaryRead,
    MintSenseGroupSummaryRequest,
    MintSenseParseRequest,
    MintSenseParseResponse,
    MintSenseResolvedParty,
)
from app.services.groups import GroupService, group_service
from app.utils.money import normalize_name_key, quantize_money

CATEGORY_KEYWORDS = {
    "dinner": "Food & Dining",
    "lunch": "Food & Dining",
    "breakfast": "Food & Dining",
    "groceries": "Groceries",
    "uber": "Transport",
    "cab": "Transport",
    "taxi": "Transport",
    "fuel": "Transport",
    "rent": "Housing",
    "hotel": "Travel",
    "flight": "Travel",
    "movie": "Entertainment",
}


@dataclass(slots=True)
class MintSenseService:
    group_service: GroupService

    def parse_expense(
        self, db: Session, owner, payload: MintSenseParseRequest
    ) -> MintSenseParseResponse:
        settings = get_settings()
        group = (
            self.group_service.get_owned_group_or_404(db, owner, payload.group_id)
            if payload.group_id
            else None
        )
        participant_names = (
            [participant.name for participant in group.participants] if group else []
        )

        if settings.ai_enabled and settings.openai_api_key:
            from app.ai.chains import LangChainMintSenseClient

            draft = LangChainMintSenseClient(settings).parse_expense(
                payload.text, participant_names
            )
        else:
            draft = self._heuristic_parse(
                payload.text,
                owner_name=owner.display_name or owner.email.split("@", 1)[0],
            )

        validation_issues: list[str] = []
        resolved_payer = None
        resolved_participants: list[MintSenseResolvedParty] = []

        if draft.amount is not None and draft.amount > 0:
            draft.amount = quantize_money(draft.amount)
        else:
            validation_issues.append("Unable to determine a positive expense amount.")

        if not draft.description:
            draft.description = payload.text.strip()

        if group:
            lookup = {
                normalize_name_key(participant.name): participant
                for participant in group.participants
            }
            owner_participant = next(
                (participant for participant in group.participants if participant.is_owner),
                None,
            )

            if draft.payer_name:
                resolved_payer = self._resolve_party(lookup, draft.payer_name, owner_participant)
                if resolved_payer is None:
                    validation_issues.append(
                        f'Payer "{draft.payer_name}" does not match a group participant.'
                    )

            for participant_name in draft.participant_names:
                resolved = self._resolve_party(lookup, participant_name, owner_participant)
                if resolved is None:
                    validation_issues.append(
                        f'Participant "{participant_name}" does not match a group participant.'
                    )
                    continue
                if not any(
                    item.participant_id == resolved.participant_id for item in resolved_participants
                ):
                    resolved_participants.append(resolved)

        if draft.split_mode in {"custom", "percentage"} and not draft.splits:
            validation_issues.append(f"{draft.split_mode.title()} split data is incomplete.")

        if draft.split_mode == "equal" and not draft.participant_names:
            validation_issues.append("Participants are required for equal splits.")

        draft.needs_confirmation = bool(validation_issues or draft.ambiguities)
        return MintSenseParseResponse(
            draft=draft,
            resolved_payer=resolved_payer,
            resolved_participants=resolved_participants,
            validation_issues=validation_issues,
        )

    def summarize_group(
        self,
        db: Session,
        owner,
        group_id: uuid.UUID,
        payload: MintSenseGroupSummaryRequest,
    ) -> MintSenseGroupSummaryRead:
        settings = get_settings()
        group = self.group_service.get_group(db, owner, group_id)
        summary_context = {
            "group_name": group.name,
            "total_spent": str(group.summary.total_spent),
            "balances": [item.model_dump(mode="json") for item in group.summary.balances],
            "settlements": [item.model_dump(mode="json") for item in group.summary.settlements],
        }

        if settings.ai_enabled and settings.openai_api_key:
            from app.ai.chains import LangChainMintSenseClient

            return LangChainMintSenseClient(settings).summarize_group(summary_context)

        highlights = []
        for settlement in group.summary.settlements[: payload.max_highlights]:
            highlights.append(
                f"{settlement.from_name} pays {settlement.to_name} {settlement.amount}"
            )
        if not highlights:
            highlights.append("All balances are already settled.")

        summary_text = (
            f"{group.name} has spent {group.summary.total_spent} in total. "
            f"{len(group.summary.balances)} participants are tracked, "
            f"and {len(group.summary.settlements)} settlement payment(s) are currently "
            f"suggested."
        )
        return MintSenseGroupSummaryRead(
            summary=summary_text,
            highlights=highlights[: payload.max_highlights],
        )

    def _resolve_party(
        self,
        lookup,
        raw_name: str,
        owner_participant,
    ) -> MintSenseResolvedParty | None:
        key = normalize_name_key(raw_name)
        if key in {"i", "me", "myself"} and owner_participant is not None:
            return MintSenseResolvedParty(
                participant_id=owner_participant.id,
                participant_name=owner_participant.name,
            )
        participant = lookup.get(key)
        if participant is None:
            return None
        return MintSenseResolvedParty(
            participant_id=participant.id,
            participant_name=participant.name,
        )

    def _heuristic_parse(self, text: str, *, owner_name: str) -> MintSenseExpenseDraft:
        normalized_text = " ".join(text.strip().split())
        lowered = normalized_text.lower()
        amount = self._extract_amount(normalized_text)
        parsed_date = self._extract_date(lowered)
        payer_name = (
            owner_name if lowered.startswith("i paid") or lowered.startswith("i spent") else None
        )
        participant_names = self._extract_participants(normalized_text)
        category = self._guess_category(lowered)
        ambiguities: list[str] = []

        if amount is None:
            ambiguities.append("Amount could not be parsed confidently.")
        if not participant_names:
            ambiguities.append("Participants could not be identified confidently.")

        return MintSenseExpenseDraft(
            description=normalized_text,
            amount=amount,
            category=category,
            date=parsed_date,
            payer_name=payer_name,
            participant_names=participant_names,
            split_mode="equal" if participant_names else None,
            splits=[],
            ambiguities=ambiguities,
            needs_confirmation=True,
        )

    @staticmethod
    def _extract_amount(text: str) -> Decimal | None:
        pattern = (
            r"(?<!\d)(?:rs\.?|inr|\u20B9|\$)?\s*"
            r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
        )
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        return Decimal(match.group(1).replace(",", ""))

    @staticmethod
    def _extract_date(text: str) -> date | None:
        today = date.today()
        if "today" in text:
            return today
        if "yesterday" in text:
            return today - timedelta(days=1)
        iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if iso_match:
            return date.fromisoformat(iso_match.group(1))
        return None

    @staticmethod
    def _extract_participants(text: str) -> list[str]:
        match = re.search(r"\bwith\s+(.+)$", text, re.IGNORECASE)
        if not match:
            return []
        tail = re.split(
            r"\bfor\b|\bsplit\b",
            match.group(1),
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        parts = [segment.strip() for segment in re.split(r",| and ", tail) if segment.strip()]
        return [part for part in parts if re.match(r"^[A-Za-z][A-Za-z .'-]{0,119}$", part)]

    @staticmethod
    def _guess_category(text: str) -> str | None:
        for keyword, category in CATEGORY_KEYWORDS.items():
            if keyword in text:
                return category
        return None


mintsense_service = MintSenseService(group_service)
