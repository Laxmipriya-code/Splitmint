"""Add product event telemetry table.

Revision ID: 20260404_0002
Revises: 20260403_0001
Create Date: 2026-04-04 20:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260404_0002"
down_revision = "20260403_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("participant_id", sa.Uuid(), nullable=True),
        sa.Column("expense_id", sa.Uuid(), nullable=True),
        sa.Column("counters", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_events_event_name", "product_events", ["event_name"], unique=False)
    op.create_index(
        "ix_product_events_created_at",
        "product_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_product_events_actor_user_id",
        "product_events",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_product_events_group_id",
        "product_events",
        ["group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_events_group_id", table_name="product_events")
    op.drop_index("ix_product_events_actor_user_id", table_name="product_events")
    op.drop_index("ix_product_events_created_at", table_name="product_events")
    op.drop_index("ix_product_events_event_name", table_name="product_events")
    op.drop_table("product_events")
