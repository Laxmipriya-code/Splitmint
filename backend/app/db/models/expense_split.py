from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class ExpenseSplit(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "expense_splits"
    __table_args__ = (
        UniqueConstraint(
            "expense_id", "participant_id", name="uq_expense_splits_expense_participant"
        ),
        Index("ix_expense_splits_participant_id", "participant_id"),
    )

    expense_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    owed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    input_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    position: Mapped[int] = mapped_column(nullable=False)

    expense = relationship("Expense", back_populates="splits")
    participant = relationship("Participant", back_populates="splits")
