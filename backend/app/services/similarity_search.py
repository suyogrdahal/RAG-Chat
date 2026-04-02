from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


async def search_similar_chunks(
    db: Session,
    org_id: UUID,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    if not query_embedding:
        return []

    safe_top_k = max(1, int(top_k))
    embedding_literal = "[" + ",".join(str(float(v)) for v in query_embedding) + "]"
    # Increase probes so ivfflat returns stable top-k results.
    db.execute(text("SET LOCAL ivfflat.probes = 100"))

    stmt = text(
        """
        SELECT
            id AS chunk_id,
            doc_id,
            content,
            embedding <=> CAST(:query_embedding AS vector) AS distance
        FROM document_chunks
        WHERE org_id = :org_id
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
        """
    )
    rows = db.execute(
        stmt,
        {
            "org_id": str(org_id),
            "query_embedding": embedding_literal,
            "top_k": safe_top_k,
        },
    ).mappings()

    results: list[dict] = []
    for row in rows:
        distance = float(row["distance"])
        score = 1.0 - distance
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "content": row["content"],
                "score": score,
            }
        )
    return results
