"""Add chat logs table.

Revision ID: 0008_add_chat_logs_table
Revises: 0007_add_org_description
Create Date: 2026-03-19 12:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0008_add_chat_logs_table"
down_revision = "0007_add_org_description"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "chat_logs" not in inspector.get_table_names():
        op.create_table(
            "chat_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "org_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("session_id", sa.Text(), nullable=True),
            sa.Column("query_text", sa.Text(), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("sources_json", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    indexes = {idx["name"] for idx in inspector.get_indexes("chat_logs")} if "chat_logs" in inspector.get_table_names() else set()
    if "ix_chat_logs_org_created_at" not in indexes:
        op.create_index("ix_chat_logs_org_created_at", "chat_logs", ["org_id", "created_at"])
    if "ix_chat_logs_org_session_id" not in indexes:
        op.create_index(
            "ix_chat_logs_org_session_id",
            "chat_logs",
            ["org_id", "session_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("chat_logs")} if "chat_logs" in inspector.get_table_names() else set()
    if "ix_chat_logs_org_session_id" in indexes:
        op.drop_index("ix_chat_logs_org_session_id", table_name="chat_logs")
    if "ix_chat_logs_org_created_at" in indexes:
        op.drop_index("ix_chat_logs_org_created_at", table_name="chat_logs")
    if "chat_logs" in inspector.get_table_names():
        op.drop_table("chat_logs")
