"""Add org memberships and active org.

Revision ID: 0003_add_org_memberships
Revises: 0002_add_refresh_tokens
Create Date: 2026-02-11 00:00:01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003_add_org_memberships"
down_revision = "0002_add_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active_org_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_users_active_org_id_organizations",
        "users",
        "organizations",
        ["active_org_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_active_org_id", "users", ["active_org_id"])

    op.create_table(
        "org_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'viewer'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "org_id", name="uq_org_memberships_user_org"),
    )
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])
    op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])

    op.execute(
        """
        INSERT INTO org_memberships (id, user_id, org_id, role, created_at)
        SELECT u.id, u.id, u.org_id, COALESCE(NULLIF(u.role, ''), 'viewer'), now()
        FROM users u
        ON CONFLICT ON CONSTRAINT uq_org_memberships_user_org DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE users
        SET active_org_id = org_id
        WHERE active_org_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_org_memberships_org_id", table_name="org_memberships")
    op.drop_index("ix_org_memberships_user_id", table_name="org_memberships")
    op.drop_table("org_memberships")

    op.drop_index("ix_users_active_org_id", table_name="users")
    op.drop_constraint("fk_users_active_org_id_organizations", "users", type_="foreignkey")
    op.drop_column("users", "active_org_id")
