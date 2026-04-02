import asyncio
from collections.abc import Generator
from uuid import uuid4

import pytest

from app.db.models import Document, DocumentChunk, DocumentStatus, Organization
from app.db.session import SessionLocal, get_db
from app.main import app
from app.services.similarity_search import search_similar_chunks


def _vec(x: float, y: float) -> list[float]:
    v = [0.0] * 384
    v[0] = x
    v[1] = y
    return v


@pytest.fixture
def db_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def override_get_db(db_session) -> Generator:
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded_chunks(db_session):
    org_a = Organization(name="Org A", slug=f"orga-{uuid4().hex[:8]}")
    org_b = Organization(name="Org B", slug=f"orgb-{uuid4().hex[:8]}")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    doc_a = Document(
        org_id=org_a.id,
        filename="a.txt",
        content_type="text/plain",
        size_bytes=10,
        status=DocumentStatus.QUEUED,
        error_message=None,
    )
    doc_b = Document(
        org_id=org_b.id,
        filename="b.txt",
        content_type="text/plain",
        size_bytes=10,
        status=DocumentStatus.QUEUED,
        error_message=None,
    )
    db_session.add_all([doc_a, doc_b])
    db_session.flush()

    # Org A chunks
    a1 = DocumentChunk(
        org_id=org_a.id,
        doc_id=doc_a.id,
        chunk_index=0,
        content="a1 most similar",
        content_hash=f"h-{uuid4().hex}",
        embedding=_vec(1.0, 0.0),
    )
    a2 = DocumentChunk(
        org_id=org_a.id,
        doc_id=doc_a.id,
        chunk_index=1,
        content="a2 medium similar",
        content_hash=f"h-{uuid4().hex}",
        embedding=_vec(0.8, 0.2),
    )
    a3 = DocumentChunk(
        org_id=org_a.id,
        doc_id=doc_a.id,
        chunk_index=2,
        content="a3 least similar",
        content_hash=f"h-{uuid4().hex}",
        embedding=_vec(0.0, 1.0),
    )

    # Org B chunk (must never be returned for Org A queries)
    b1 = DocumentChunk(
        org_id=org_b.id,
        doc_id=doc_b.id,
        chunk_index=0,
        content="b1 other org",
        content_hash=f"h-{uuid4().hex}",
        embedding=_vec(1.0, 0.0),
    )
    db_session.add_all([a1, a2, a3, b1])
    db_session.commit()

    try:
        yield {
            "org_a_id": org_a.id,
            "org_b_id": org_b.id,
            "doc_a_id": doc_a.id,
            "doc_b_id": doc_b.id,
        }
    finally:
        db_session.delete(org_a)
        db_session.delete(org_b)
        db_session.commit()


def test_search_similar_chunks_returns_top_k_for_org_id(
    db_session,
    override_get_db,
    seeded_chunks,
) -> None:
    query_embedding = _vec(1.0, 0.0)
    results = asyncio.run(
        search_similar_chunks(
            db=db_session,
            org_id=seeded_chunks["org_a_id"],
            query_embedding=query_embedding,
            top_k=2,
        )
    )
    assert len(results) == 2
    assert all(item["doc_id"] == seeded_chunks["doc_a_id"] for item in results)


def test_search_similar_chunks_org_isolation(
    db_session,
    override_get_db,
    seeded_chunks,
) -> None:
    query_embedding = _vec(1.0, 0.0)
    results = asyncio.run(
        search_similar_chunks(
            db=db_session,
            org_id=seeded_chunks["org_a_id"],
            query_embedding=query_embedding,
            top_k=10,
        )
    )
    assert results
    assert all(item["doc_id"] != seeded_chunks["doc_b_id"] for item in results)


def test_search_similar_chunks_ordered_by_similarity_score_desc(
    db_session,
    override_get_db,
    seeded_chunks,
) -> None:
    query_embedding = _vec(1.0, 0.0)
    results = asyncio.run(
        search_similar_chunks(
            db=db_session,
            org_id=seeded_chunks["org_a_id"],
            query_embedding=query_embedding,
            top_k=3,
        )
    )
    assert len(results) == 3
    scores = [float(r["score"]) for r in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["content"] == "a1 most similar"
