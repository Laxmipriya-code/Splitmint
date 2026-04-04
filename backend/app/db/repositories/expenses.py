from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import Expense, ExpenseSplit, Group


class ExpenseRepository:
    def get_for_owner(
        self, db: Session, expense_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Expense | None:
        stmt = (
            select(Expense)
            .join(Expense.group)
            .where(Expense.id == expense_id, Group.owner_id == owner_id)
            .options(
                joinedload(Expense.payer),
                joinedload(Expense.group),
                selectinload(Expense.splits).joinedload(ExpenseSplit.participant),
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_group(
        self,
        db: Session,
        *,
        owner_id: uuid.UUID,
        group_id: uuid.UUID,
        search: str | None,
        participant_id: uuid.UUID | None,
        date_from: date | None,
        date_to: date | None,
        min_amount: Decimal | None,
        max_amount: Decimal | None,
        page: int,
        size: int,
    ) -> tuple[Sequence[Expense], int]:
        filters = [Expense.group_id == group_id, Group.owner_id == owner_id]

        if search:
            pattern = f"%{search.strip()}%"
            filters.append(or_(Expense.description.ilike(pattern), Expense.category.ilike(pattern)))

        if participant_id:
            split_subquery = select(ExpenseSplit.expense_id).where(
                ExpenseSplit.participant_id == participant_id
            )
            filters.append(or_(Expense.payer_id == participant_id, Expense.id.in_(split_subquery)))

        if date_from:
            filters.append(Expense.expense_date >= date_from)
        if date_to:
            filters.append(Expense.expense_date <= date_to)
        if min_amount is not None:
            filters.append(Expense.amount >= min_amount)
        if max_amount is not None:
            filters.append(Expense.amount <= max_amount)

        base_stmt = select(Expense).join(Expense.group).where(and_(*filters))
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        items_stmt = (
            base_stmt.options(
                joinedload(Expense.payer),
                selectinload(Expense.splits).joinedload(ExpenseSplit.participant),
            )
            .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        total = db.execute(count_stmt).scalar_one()
        items = db.execute(items_stmt).scalars().unique().all()
        return items, total

    def create(self, db: Session, expense: Expense) -> Expense:
        db.add(expense)
        db.flush()
        return expense

    def delete(self, db: Session, expense: Expense) -> None:
        db.delete(expense)

    def participant_has_history(self, db: Session, participant_id: uuid.UUID) -> bool:
        expense_exists = db.execute(
            select(Expense.id).where(Expense.payer_id == participant_id).limit(1)
        ).first()
        split_exists = db.execute(
            select(ExpenseSplit.id).where(ExpenseSplit.participant_id == participant_id).limit(1)
        ).first()
        return bool(expense_exists or split_exists)

    def clear_expense_splits(self, expense: Expense) -> None:
        expense.splits.clear()
