from uuid import uuid4

import pytest

from app.db.models import Document, DocumentChunk, DocumentStatus, Organization
from app.db.session import SessionLocal
from app.ingestion.chunking import chunk_text
from app.ingestion.pipeline import build_chunk_rows
from app.repositories.vector_repository import VectorRepository


def _create_org_and_doc():
    session = SessionLocal()
    try:
        org = Organization(name=f"Org-{uuid4().hex[:6]}", slug=f"org-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        doc = Document(
            org_id=org.id,
            filename="doc.txt",
            content_type="text/plain",
            size_bytes=100,
            status=DocumentStatus.QUEUED,
            error_message=None,
        )
        session.add(doc)
        session.commit()
        session.refresh(org)
        session.refresh(doc)
        return org.id, doc.id
    finally:
        session.close()


def _cleanup_org(org_id):
    session = SessionLocal()
    try:
        org = session.get(Organization, org_id)
        if org is not None:
            session.delete(org)
        session.commit()
    finally:
        session.close()


def test_ingest_creates_only_rows_with_correct_org_id_doc_id() -> None:
    org_id, doc_id = _create_org_and_doc()
    try:
        text = (
            "Paragraph one for metadata test. " * 40
            + "\n\n"
            + "Paragraph two for metadata test. " * 40
        )
        chunks = chunk_text(text)
        embeddings = [[0.001] * 384 for _ in chunks]
        rows = build_chunk_rows(org_id=org_id, doc_id=doc_id, text=text, embeddings=embeddings)

        session = SessionLocal()
        try:
            repo = VectorRepository(session)
            saved = repo.insert_chunks_with_embeddings(org_id=org_id, doc_id=doc_id, rows=rows)
            assert saved
            assert all(str(c.org_id) == str(org_id) for c in saved)
            assert all(str(c.doc_id) == str(doc_id) for c in saved)
            assert all(c.content_hash for c in saved)

            db_rows = (
                session.query(DocumentChunk)
                .filter(DocumentChunk.org_id == org_id, DocumentChunk.doc_id == doc_id)
                .all()
            )
            assert len(db_rows) == len(saved)
        finally:
            session.close()
    finally:
        _cleanup_org(org_id)


def test_cross_org_insert_not_possible() -> None:
    org_a_id, _ = _create_org_and_doc()
    org_b_id, doc_b_id = _create_org_and_doc()
    try:
        text = "Cross org insert must fail. " * 50
        chunks = chunk_text(text)
        embeddings = [[0.002] * 384 for _ in chunks]
        rows = build_chunk_rows(org_id=org_b_id, doc_id=doc_b_id, text=text, embeddings=embeddings)

        session = SessionLocal()
        try:
            repo = VectorRepository(session)
            with pytest.raises(ValueError):
                repo.insert_chunks_with_embeddings(org_id=org_a_id, doc_id=doc_b_id, rows=rows)
        finally:
            session.close()
    finally:
        _cleanup_org(org_a_id)
        _cleanup_org(org_b_id)
