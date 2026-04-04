from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionedMixin


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_group_id", "group_id"),
        Index("ix_expenses_group_date", "group_id", "expense_date"),
        Index("ix_expenses_payer_id", "payer_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    payer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    split_mode: Mapped[str] = mapped_column(
        Enum("equal", "custom", "percentage", name="split_mode_enum"),
        nullable=False,
    )
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)

    group = relationship("Group", back_populates="expenses")
    payer = relationship("Participant", back_populates="paid_expenses")
    splits = relationship(
        "ExpenseSplit",
        back_populates="expense",
        cascade="all, delete-orphan",
        order_by="ExpenseSplit.position",
    )
