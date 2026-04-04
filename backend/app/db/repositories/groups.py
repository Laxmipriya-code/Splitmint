from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Expense, ExpenseSplit, Group, Participant


class GroupRepository:
    def create(self, db: Session, group: Group) -> Group:
        db.add(group)
        db.flush()
        return group

    def list_for_owner(self, db: Session, owner_id: uuid.UUID) -> Sequence[Group]:
        stmt = (
            select(Group)
            .where(Group.owner_id == owner_id)
            .options(
                selectinload(Group.participants),
                selectinload(Group.expenses).selectinload(Expense.splits),
            )
            .order_by(Group.created_at.desc())
        )
        return db.execute(stmt).scalars().unique().all()

    def get_for_owner(self, db: Session, group_id: uuid.UUID, owner_id: uuid.UUID) -> Group | None:
        stmt = (
            select(Group)
            .where(Group.id == group_id, Group.owner_id == owner_id)
            .options(
                selectinload(Group.participants),
                selectinload(Group.expenses).joinedload(Expense.payer),
                selectinload(Group.expenses)
                .selectinload(Expense.splits)
                .joinedload(ExpenseSplit.participant),
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_for_owner_basic(
        self, db: Session, group_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Group | None:
        stmt = (
            select(Group)
            .where(Group.id == group_id, Group.owner_id == owner_id)
            .options(selectinload(Group.participants))
        )
        return db.execute(stmt).scalar_one_or_none()

    def delete(self, db: Session, group: Group) -> None:
        db.delete(group)

    def active_participant_count(self, db: Session, group_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Participant)
            .where(
                Participant.group_id == group_id,
                Participant.is_active.is_(True),
            )
        )
        return db.execute(stmt).scalar_one()
