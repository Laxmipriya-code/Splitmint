from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionedMixin


class Participant(UUIDPrimaryKeyMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("group_id", "name_key", name="uq_participants_group_name_key"),
        Index("ix_participants_group_id", "group_id"),
        Index("ix_participants_group_active", "group_id", "is_active"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    group = relationship("Group", back_populates="participants")
    linked_user = relationship("User", back_populates="owned_participants")
    paid_expenses = relationship("Expense", back_populates="payer")
    splits = relationship("ExpenseSplit", back_populates="participant")
