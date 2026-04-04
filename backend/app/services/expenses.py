from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.db.models import Expense, ExpenseSplit, Group, Participant, User
from app.db.repositories.expenses import ExpenseRepository
from app.db.repositories.groups import GroupRepository
from app.schemas.expense import ExpenseListRead, ExpenseRead, ExpenseUpsertRequest
from app.services.ledger import ExpenseSplitNormalizer, expense_split_normalizer
from app.utils.money import ensure_money_precision, ensure_percentage_precision


@dataclass(slots=True)
class ExpenseService:
    expense_repository: ExpenseRepository
    group_repository: GroupRepository
    split_normalizer: ExpenseSplitNormalizer

    def create_expense(
        self, db: Session, owner: User, payload: ExpenseUpsertRequest
    ) -> ExpenseRead:
        group = self._get_group_with_owner_check(db, owner.id, payload.group_id)
        amount = ensure_money_precision(payload.amount, field_name="amount")
        payer, participants = self._resolve_participants(
            group, payload.payer_id, payload.participants
        )
        normalized_splits = self._normalize_splits(amount, payload)

        expense = Expense(
            group_id=group.id,
            payer_id=payer.id,
            amount=amount,
            description=payload.description,
            category=payload.category,
            split_mode=payload.split_mode,
            expense_date=payload.date,
        )
        expense.splits = [
            ExpenseSplit(
                participant_id=split.participant_id,
                owed_amount=split.owed_amount,
                input_value=split.input_value,
                position=split.position,
            )
            for split in normalized_splits
        ]
        self.expense_repository.create(db, expense)
        db.commit()
        reloaded = self.expense_repository.get_for_owner(db, expense.id, owner.id)
        return self._to_expense_read(reloaded)

    def update_expense(
        self,
        db: Session,
        owner: User,
        expense_id: uuid.UUID,
        payload: ExpenseUpsertRequest,
    ) -> ExpenseRead:
        expense = self.expense_repository.get_for_owner(db, expense_id, owner.id)
        if expense is None:
            raise NotFoundError("Expense not found", code="expense_not_found")

        group = self._get_group_with_owner_check(db, owner.id, payload.group_id)
        amount = ensure_money_precision(payload.amount, field_name="amount")
        grandfathered_ids = {expense.payer_id, *[split.participant_id for split in expense.splits]}
        payer, participants = self._resolve_participants(
            group,
            payload.payer_id,
            payload.participants,
            grandfathered_ids=grandfathered_ids if payload.group_id == expense.group_id else None,
        )
        normalized_splits = self._normalize_splits(amount, payload)

        expense.group_id = group.id
        expense.payer_id = payer.id
        expense.amount = amount
        expense.description = payload.description
        expense.category = payload.category
        expense.split_mode = payload.split_mode
        expense.expense_date = payload.date
        expense.splits.clear()
        db.flush()
        expense.splits = [
            ExpenseSplit(
                participant_id=split.participant_id,
                owed_amount=split.owed_amount,
                input_value=split.input_value,
                position=split.position,
            )
            for split in normalized_splits
        ]

        db.commit()
        reloaded = self.expense_repository.get_for_owner(db, expense.id, owner.id)
        return self._to_expense_read(reloaded)

    def delete_expense(self, db: Session, owner: User, expense_id: uuid.UUID) -> None:
        expense = self.expense_repository.get_for_owner(db, expense_id, owner.id)
        if expense is None:
            raise NotFoundError("Expense not found", code="expense_not_found")
        self.expense_repository.delete(db, expense)
        db.commit()

    def get_expense(self, db: Session, owner: User, expense_id: uuid.UUID) -> ExpenseRead:
        expense = self.expense_repository.get_for_owner(db, expense_id, owner.id)
        if expense is None:
            raise NotFoundError("Expense not found", code="expense_not_found")
        return self._to_expense_read(expense)

    def list_expenses(
        self,
        db: Session,
        owner: User,
        *,
        group_id: uuid.UUID,
        search: str | None,
        participant_id: uuid.UUID | None,
        date_from,
        date_to,
        min_amount,
        max_amount,
        page: int,
        size: int,
    ) -> ExpenseListRead:
        self._get_group_with_owner_check(db, owner.id, group_id)
        min_amount = (
            ensure_money_precision(min_amount, field_name="min_amount")
            if min_amount is not None
            else None
        )
        max_amount = (
            ensure_money_precision(max_amount, field_name="max_amount")
            if max_amount is not None
            else None
        )
        items, total = self.expense_repository.list_for_group(
            db,
            owner_id=owner.id,
            group_id=group_id,
            search=search,
            participant_id=participant_id,
            date_from=date_from,
            date_to=date_to,
            min_amount=min_amount,
            max_amount=max_amount,
            page=page,
            size=size,
        )
        return ExpenseListRead(
            items=[self._to_expense_read(item) for item in items],
            total=total,
            page=page,
            size=size,
        )

    def _normalize_splits(self, amount, payload: ExpenseUpsertRequest):
        split_values: dict[uuid.UUID, object] = {}
        if payload.split_mode == "custom":
            split_values = {
                item.participant_id: ensure_money_precision(
                    item.value, field_name=f"split:{item.participant_id}"
                )
                for item in payload.splits
            }
        elif payload.split_mode == "percentage":
            split_values = {
                item.participant_id: ensure_percentage_precision(
                    item.value,
                    field_name=f"split:{item.participant_id}",
                )
                for item in payload.splits
            }
        return self.split_normalizer.normalize(
            amount=amount,
            participant_ids=payload.participants,
            split_mode=payload.split_mode,
            split_values=split_values,
        )

    def _resolve_participants(
        self,
        group: Group,
        payer_id: uuid.UUID,
        participant_ids: list[uuid.UUID],
        *,
        grandfathered_ids: set[uuid.UUID] | None = None,
    ) -> tuple[Participant, list[Participant]]:
        participant_map = {participant.id: participant for participant in group.participants}
        payer = participant_map.get(payer_id)
        if payer is None:
            raise BadRequestError("Payer does not belong to the group")
        self._ensure_active_or_grandfathered(payer, grandfathered_ids)

        participants: list[Participant] = []
        for participant_id in participant_ids:
            participant = participant_map.get(participant_id)
            if participant is None:
                raise BadRequestError("One or more split participants do not belong to the group")
            self._ensure_active_or_grandfathered(participant, grandfathered_ids)
            participants.append(participant)
        return payer, participants

    @staticmethod
    def _ensure_active_or_grandfathered(
        participant: Participant,
        grandfathered_ids: set[uuid.UUID] | None,
    ) -> None:
        if participant.is_active:
            return
        if grandfathered_ids and participant.id in grandfathered_ids:
            return
        raise BadRequestError("Inactive participants cannot be added to new expenses")

    def _get_group_with_owner_check(
        self, db: Session, owner_id: uuid.UUID, group_id: uuid.UUID
    ) -> Group:
        group = self.group_repository.get_for_owner_basic(db, group_id, owner_id)
        if group is None:
            raise NotFoundError("Group not found", code="group_not_found")
        return group

    @staticmethod
    def _to_expense_read(expense: Expense) -> ExpenseRead:
        return ExpenseRead(
            id=expense.id,
            group_id=expense.group_id,
            payer_id=expense.payer_id,
            payer_name=expense.payer.name,
            amount=expense.amount,
            description=expense.description,
            category=expense.category,
            split_mode=expense.split_mode,
            date=expense.expense_date,
            splits=[
                {
                    "participant_id": split.participant_id,
                    "participant_name": split.participant.name,
                    "owed_amount": split.owed_amount,
                    "input_value": split.input_value,
                    "position": split.position,
                }
                for split in expense.splits
            ],
            created_at=expense.created_at,
            updated_at=expense.updated_at,
            version=expense.version,
        )


expense_service = ExpenseService(ExpenseRepository(), GroupRepository(), expense_split_normalizer)
