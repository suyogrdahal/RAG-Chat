"""Add organization_description to organizations.

Revision ID: 0007_add_org_description
Revises: 0006_add_widget_public_key
Create Date: 2026-02-19 00:00:01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_org_description"
down_revision = "0006_add_widget_public_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("organizations")}
    if "organization_description" not in columns:
        op.add_column("organizations", sa.Column("organization_description", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("organizations")}
    if "organization_description" in columns:
        op.drop_column("organizations", "organization_description")
