from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProductEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_events"
    __table_args__ = (
        Index("ix_product_events_event_name", "event_name"),
        Index("ix_product_events_created_at", "created_at"),
        Index("ix_product_events_actor_user_id", "actor_user_id"),
        Index("ix_product_events_group_id", "group_id"),
    )

    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    expense_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL"),
        nullable=True,
    )
    counters: Mapped[dict[str, int | float | bool]] = mapped_column(JSON, nullable=False, default=dict)
