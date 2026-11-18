"""initial tables

Revision ID: 001_initial
Revises:
Create Date: 2026-11-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("domain_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("traffic_source_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "local_streams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("keitaro_stream_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("has_offers", sa.Boolean(), nullable=False),
        sa.Column("is_dirty", sa.Boolean(), nullable=False),
        sa.Column("published_snapshot", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keitaro_stream_id"),
    )
    op.create_index("ix_local_streams_campaign_id", "local_streams", ["campaign_id"])
    op.create_table(
        "local_offers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_id", sa.Integer(), nullable=False),
        sa.Column("keitaro_offer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("share", sa.Integer(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["stream_id"], ["local_streams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_local_offers_keitaro_offer_id", "local_offers", ["keitaro_offer_id"])


def downgrade() -> None:
    op.drop_index("ix_local_offers_keitaro_offer_id", table_name="local_offers")
    op.drop_table("local_offers")
    op.drop_index("ix_local_streams_campaign_id", table_name="local_streams")
    op.drop_table("local_streams")
    op.drop_table("operation_logs")
    op.drop_table("app_settings")
