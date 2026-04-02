from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
import re
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk


@dataclass
class ChunkEmbeddingRow:
    org_id: UUID
    doc_id: UUID
    chunk_index: int
    content: str
    embedding: list[float]
    content_hash: str | None = None


def _normalize_for_hash(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    return normalized


def _content_hash(content: str) -> str:
    return sha256(_normalize_for_hash(content).encode("utf-8")).hexdigest()


class VectorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def insert_chunks_with_embeddings(
        self,
        org_id: UUID,
        doc_id: UUID,
        rows: Sequence[ChunkEmbeddingRow | dict],
    ) -> list[DocumentChunk]:
        doc = self.db.scalar(
            select(Document).where(Document.id == doc_id, Document.org_id == org_id)
        )
        if doc is None:
            raise ValueError("Document does not belong to organization")

        chunks: list[DocumentChunk] = []
        for row in rows:
            payload = row if isinstance(row, dict) else row.__dict__
            row_org_id = payload.get("org_id", org_id)
            row_doc_id = payload.get("doc_id", doc_id)
            if str(row_org_id) != str(org_id) or str(row_doc_id) != str(doc_id):
                raise ValueError("Chunk metadata org_id/doc_id mismatch")
            content = str(payload["content"])
            chunk = DocumentChunk(
                org_id=org_id,
                doc_id=doc_id,
                chunk_index=int(payload["chunk_index"]),
                content=content,
                content_hash=str(payload.get("content_hash") or _content_hash(content)),
                embedding=list(payload["embedding"]),
            )
            self.db.add(chunk)
            chunks.append(chunk)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def similarity_search(
        self,
        org_id: UUID,
        query_embedding: Sequence[float],
        top_k: int,
        doc_id: UUID | None = None,
    ) -> list[dict]:
        embedding_literal = "[" + ",".join(str(float(v)) for v in query_embedding) + "]"
        if doc_id is None:
            stmt = text(
                """
                SELECT
                    id,
                    org_id,
                    doc_id,
                    chunk_index,
                    content,
                    content_hash,
                    created_at,
                    embedding <=> CAST(:query_embedding AS vector) AS distance
                FROM document_chunks
                WHERE org_id = :org_id
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
                """
            )
            params = {
                "org_id": str(org_id),
                "query_embedding": embedding_literal,
                "top_k": int(top_k),
            }
        else:
            stmt = text(
                """
                SELECT
                    id,
                    org_id,
                    doc_id,
                    chunk_index,
                    content,
                    content_hash,
                    created_at,
                    embedding <=> CAST(:query_embedding AS vector) AS distance
                FROM document_chunks
                WHERE org_id = :org_id
                  AND doc_id = :doc_id
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
                """
            )
            params = {
                "org_id": str(org_id),
                "doc_id": str(doc_id),
                "query_embedding": embedding_literal,
                "top_k": int(top_k),
            }
        result = self.db.execute(stmt, params)
        return [dict(row._mapping) for row in result]
