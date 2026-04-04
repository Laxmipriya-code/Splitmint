"""Initial SplitMint schema.

Revision ID: 20260403_0001
Revises:
Create Date: 2026-04-03 23:59:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260403_0001"
down_revision = None
branch_labels = None
depends_on = None


split_mode_enum = sa.Enum("equal", "custom", "percentage", name="split_mode_enum")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_owner_id", "groups", ["owner_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "name_key", name="uq_participants_group_name_key"),
    )
    op.create_index("ix_participants_group_active", "participants", ["group_id", "is_active"], unique=False)
    op.create_index("ix_participants_group_id", "participants", ["group_id"], unique=False)

    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("split_mode", split_mode_enum, nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payer_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_group_date", "expenses", ["group_id", "expense_date"], unique=False)
    op.create_index("ix_expenses_group_id", "expenses", ["group_id"], unique=False)
    op.create_index("ix_expenses_payer_id", "expenses", ["payer_id"], unique=False)

    op.create_table(
        "expense_splits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("expense_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("owed_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("input_value", sa.Numeric(14, 4), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("owed_amount > 0", name="ck_expense_splits_owed_positive"),
        sa.ForeignKeyConstraint(["expense_id"], ["expenses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expense_id", "participant_id", name="uq_expense_splits_expense_participant"),
    )
    op.create_index("ix_expense_splits_participant_id", "expense_splits", ["participant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expense_splits_participant_id", table_name="expense_splits")
    op.drop_table("expense_splits")
    op.drop_index("ix_expenses_payer_id", table_name="expenses")
    op.drop_index("ix_expenses_group_id", table_name="expenses")
    op.drop_index("ix_expenses_group_date", table_name="expenses")
    op.drop_table("expenses")
    split_mode_enum.drop(op.get_bind(), checkfirst=False)
    op.drop_index("ix_participants_group_id", table_name="participants")
    op.drop_index("ix_participants_group_active", table_name="participants")
    op.drop_table("participants")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_groups_owner_id", table_name="groups")
    op.drop_table("groups")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
