"""Create documents and vector storage tables.

Revision ID: 0005_docs_vector_tables
Revises: 0004_enable_pgvector_extension
Create Date: 2026-02-12 00:00:01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


class Vector384(sa.types.UserDefinedType):
    def get_col_spec(self, **kw):
        return "vector(384)"


# revision identifiers, used by Alembic.
revision = "0005_docs_vector_tables"
down_revision = "0004_enable_pgvector_extension"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    document_status = postgresql.ENUM(
        "queued",
        "processing",
        "succeeded",
        "failed",
        name="document_status",
        create_type=False,
    )
    document_status.create(bind, checkfirst=True)

    if not inspector.has_table("documents"):
        op.create_table(
            "documents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "org_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("filename", sa.Text(), nullable=False),
            sa.Column("content_type", sa.Text(), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column(
                "status",
                document_status,
                nullable=False,
                server_default=sa.text("'queued'"),
            ),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_org_id ON documents (org_id)")

    if not inspector.has_table("document_chunks"):
        op.create_table(
            "document_chunks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column(
                "org_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "doc_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.Text(), nullable=False),
            sa.Column("embedding", Vector384(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_org_id_doc_id "
        "ON document_chunks (org_id, doc_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_doc_id ON document_chunks (doc_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_org_doc_chunk_hash "
        "ON document_chunks (org_id, doc_id, chunk_index, content_hash)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.execute("DROP INDEX IF EXISTS uq_document_chunks_org_doc_chunk_hash")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_doc_id")
    op.drop_index("ix_document_chunks_org_id_doc_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_org_id", table_name="documents")
    op.drop_table("documents")

    document_status = postgresql.ENUM(
        "queued",
        "processing",
        "succeeded",
        "failed",
        name="document_status",
        create_type=False,
    )
    document_status.drop(op.get_bind(), checkfirst=True)
