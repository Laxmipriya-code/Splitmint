from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from app.db.models import Group, Participant
from app.schemas.balance import BalanceSnapshotRead, ParticipantBalanceRead, SettlementRead
from app.utils.money import CENT, ZERO, quantize_money


@dataclass(slots=True)
class BalanceService:
    def build_snapshot(self, group: Group) -> BalanceSnapshotRead:
        participants = sorted(
            group.participants,
            key=lambda item: (not item.is_owner, item.name.lower(), str(item.id)),
        )
        paid_totals = defaultdict(lambda: ZERO)
        owed_totals = defaultdict(lambda: ZERO)

        for expense in group.expenses:
            paid_totals[expense.payer_id] = quantize_money(
                paid_totals[expense.payer_id] + expense.amount
            )
            for split in expense.splits:
                owed_totals[split.participant_id] = quantize_money(
                    owed_totals[split.participant_id] + split.owed_amount
                )

        balances: list[ParticipantBalanceRead] = []
        net_by_id: dict[uuid.UUID, Decimal] = {}
        total_spent = ZERO

        for expense in group.expenses:
            total_spent = quantize_money(total_spent + expense.amount)

        owner_participant = next(
            (participant for participant in participants if participant.is_owner), None
        )

        for participant in participants:
            paid_total = quantize_money(paid_totals[participant.id])
            owed_total = quantize_money(owed_totals[participant.id])
            net_balance = quantize_money(paid_total - owed_total)
            if abs(net_balance) < CENT:
                net_balance = ZERO
            net_by_id[participant.id] = net_balance
            balances.append(
                ParticipantBalanceRead(
                    participant_id=participant.id,
                    name=participant.name,
                    color_hex=participant.color_hex,
                    is_active=participant.is_active,
                    is_owner=participant.is_owner,
                    paid_total=paid_total,
                    owed_total=owed_total,
                    net_balance=net_balance,
                )
            )

        settlements = self._build_settlements(participants, net_by_id)
        owner_balance = net_by_id.get(owner_participant.id, ZERO) if owner_participant else ZERO
        you_owe = abs(owner_balance) if owner_balance < ZERO else ZERO
        you_are_owed = owner_balance if owner_balance > ZERO else ZERO

        return BalanceSnapshotRead(
            total_spent=total_spent,
            you_owe=quantize_money(you_owe),
            you_are_owed=quantize_money(you_are_owed),
            balances=balances,
            settlements=settlements,
        )

    def _build_settlements(
        self,
        participants: list[Participant],
        net_by_id: dict[uuid.UUID, Decimal],
    ) -> list[SettlementRead]:
        participant_lookup = {participant.id: participant for participant in participants}
        creditors = [
            [participant_id, balance]
            for participant_id, balance in net_by_id.items()
            if balance > ZERO
        ]
        debtors = [
            [participant_id, balance]
            for participant_id, balance in net_by_id.items()
            if balance < ZERO
        ]
        creditors.sort(
            key=lambda item: (
                -item[1],
                participant_lookup[item[0]].name.lower(),
                str(item[0]),
            )
        )
        debtors.sort(
            key=lambda item: (
                item[1],
                participant_lookup[item[0]].name.lower(),
                str(item[0]),
            )
        )

        settlements: list[SettlementRead] = []
        creditor_index = 0
        debtor_index = 0

        while creditor_index < len(creditors) and debtor_index < len(debtors):
            creditor_id, creditor_amount = creditors[creditor_index]
            debtor_id, debtor_amount = debtors[debtor_index]
            settled_amount = quantize_money(min(creditor_amount, abs(debtor_amount)))

            if settled_amount > ZERO:
                settlements.append(
                    SettlementRead(
                        from_participant_id=debtor_id,
                        from_name=participant_lookup[debtor_id].name,
                        to_participant_id=creditor_id,
                        to_name=participant_lookup[creditor_id].name,
                        amount=settled_amount,
                    )
                )

            creditors[creditor_index][1] = quantize_money(creditor_amount - settled_amount)
            debtors[debtor_index][1] = quantize_money(debtor_amount + settled_amount)

            if creditors[creditor_index][1] == ZERO:
                creditor_index += 1
            if debtors[debtor_index][1] == ZERO:
                debtor_index += 1

        return settlements


balance_service = BalanceService()
