from __future__ import annotations

from hashlib import sha256
import re
from uuid import UUID

from app.ingestion.chunking import Chunk, chunk_text


def _normalize_for_hash(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    return normalized


def _content_hash(content: str) -> str:
    return sha256(_normalize_for_hash(content).encode("utf-8")).hexdigest()


def build_chunk_rows(
    org_id: UUID,
    doc_id: UUID,
    text: str,
    embeddings: list[list[float]],
) -> list[dict]:
    chunks: list[Chunk] = chunk_text(text)
    if len(chunks) != len(embeddings):
        raise ValueError("embeddings count must match chunk count")

    rows: list[dict] = []
    for idx, chunk in enumerate(chunks):
        rows.append(
            {
                "org_id": org_id,
                "doc_id": doc_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "content_hash": _content_hash(chunk.content),
                "embedding": embeddings[idx],
            }
        )
    return rows
