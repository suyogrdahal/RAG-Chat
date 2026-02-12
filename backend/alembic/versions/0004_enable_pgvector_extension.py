"""Enable pgvector extension.

Revision ID: 0004_enable_pgvector_extension
Revises: 0003_add_org_memberships
Create Date: 2026-02-12 00:00:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_enable_pgvector_extension"
down_revision = "0003_add_org_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
