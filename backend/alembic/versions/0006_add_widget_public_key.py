"""Add widget public key to organizations.

Revision ID: 0006_add_widget_public_key
Revises: 0005_docs_vector_tables
Create Date: 2026-02-18 00:00:01
"""

import secrets

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006_add_widget_public_key"
down_revision = "0005_docs_vector_tables"
branch_labels = None
depends_on = None


def _generate_key() -> str:
    return secrets.token_urlsafe(24)


def upgrade() -> None:
    op.add_column("organizations", sa.Column("widget_public_key", sa.Text(), nullable=True))

    bind = op.get_bind()
    organizations = sa.table(
        "organizations",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("widget_public_key", sa.Text()),
    )
    rows = bind.execute(
        sa.select(organizations.c.id).where(organizations.c.widget_public_key.is_(None))
    ).fetchall()
    for row in rows:
        bind.execute(
            organizations.update()
            .where(organizations.c.id == row.id)
            .values(widget_public_key=_generate_key())
        )

    op.alter_column("organizations", "widget_public_key", nullable=False)
    op.create_unique_constraint(
        "uq_organizations_widget_public_key",
        "organizations",
        ["widget_public_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_organizations_widget_public_key", "organizations", type_="unique")
    op.drop_column("organizations", "widget_public_key")
