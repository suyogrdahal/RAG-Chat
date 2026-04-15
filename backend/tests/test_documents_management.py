from pathlib import Path
from shutil import rmtree
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import Document, DocumentChunk, DocumentStatus, OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _setup_org_user(prefix: str):
    session = SessionLocal()
    try:
        org = Organization(name=f"{prefix} Org", slug=f"{prefix}-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=f"{prefix}-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
            role="admin",
            is_active=True,
        )
        session.add(user)
        session.flush()
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
        session.commit()
        session.refresh(org)
        session.refresh(user)
        return org, user
    finally:
        session.close()


def _cleanup(org_id=None, user_id=None) -> None:
    session = SessionLocal()
    try:
        if user_id is not None:
            user = session.get(User, user_id)
            if user is not None:
                session.delete(user)
        if org_id is not None:
            org = session.get(Organization, org_id)
            if org is not None:
                session.delete(org)
        session.commit()
    finally:
        session.close()
    if org_id is not None:
        org_path = Path("data") / str(org_id)
        if org_path.exists():
            rmtree(org_path, ignore_errors=True)


def _auth_headers(user_id, org_id) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "org_id": str(org_id), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def _create_document(session, org_id, status: DocumentStatus) -> Document:
    doc = Document(
        org_id=org_id,
        filename=f"doc-{uuid4().hex[:8]}.txt",
        content_type="text/plain",
        size_bytes=50,
        status=status,
        error_message="old failure" if status == DocumentStatus.FAILED else None,
    )
    session.add(doc)
    session.flush()
    return doc


def _create_chunk(session, org_id, doc_id, chunk_index: int, content: str) -> None:
    embedding = [0.0] * 384
    embedding[0] = float(chunk_index + 1)
    session.add(
        DocumentChunk(
            org_id=org_id,
            doc_id=doc_id,
            chunk_index=chunk_index,
            content=content,
            content_hash=f"hash-{uuid4().hex}",
            embedding=embedding,
        )
    )
    session.flush()


def test_reingest_deletes_old_chunks(monkeypatch) -> None:
    org, user = _setup_org_user("reingest-old")
    try:
        session = SessionLocal()
        try:
            doc = _create_document(session, org.id, DocumentStatus.FAILED)
            _create_chunk(session, org.id, doc.id, 0, "old chunk")
            session.commit()
            doc_id = doc.id
        finally:
            session.close()

        from app.api import documents as documents_api

        def _fake_run(doc_id: UUID, org_id: UUID, repo) -> None:
            repo.db.add(
                DocumentChunk(
                    org_id=org_id,
                    doc_id=doc_id,
                    chunk_index=0,
                    content="new chunk",
                    content_hash=f"hash-{uuid4().hex}",
                    embedding=[0.1] * 384,
                )
            )
            repo.db.commit()

        monkeypatch.setattr(documents_api, "_run_ingestion_pipeline", _fake_run)

        response = client.post(
            f"/documents/{doc_id}/reingest",
            headers=_auth_headers(user.id, org.id),
        )
        assert response.status_code == 200, response.text

        session = SessionLocal()
        try:
            chunks = (
                session.query(DocumentChunk)
                .filter(DocumentChunk.org_id == org.id, DocumentChunk.doc_id == doc_id)
                .all()
            )
            assert len(chunks) == 1
            assert chunks[0].content == "new chunk"
        finally:
            session.close()
    finally:
        _cleanup(org.id, user.id)


def test_reingest_works_for_failed_and_completed(monkeypatch) -> None:
    org, user = _setup_org_user("reingest-states")
    try:
        session = SessionLocal()
        try:
            failed_doc = _create_document(session, org.id, DocumentStatus.FAILED)
            completed_doc = _create_document(session, org.id, DocumentStatus.SUCCEEDED)
            session.commit()
            failed_doc_id = failed_doc.id
            completed_doc_id = completed_doc.id
        finally:
            session.close()

        from app.api import documents as documents_api

        def _fake_run(doc_id: UUID, org_id: UUID, repo) -> None:
            repo.db.add(
                DocumentChunk(
                    org_id=org_id,
                    doc_id=doc_id,
                    chunk_index=0,
                    content="chunk",
                    content_hash=f"hash-{uuid4().hex}",
                    embedding=[0.2] * 384,
                )
            )
            repo.db.commit()

        monkeypatch.setattr(documents_api, "_run_ingestion_pipeline", _fake_run)

        for doc_id in (failed_doc_id, completed_doc_id):
            response = client.post(
                f"/documents/{doc_id}/reingest",
                headers=_auth_headers(user.id, org.id),
            )
            assert response.status_code == 200, response.text

        session = SessionLocal()
        try:
            failed_doc = session.get(Document, failed_doc_id)
            completed_doc = session.get(Document, completed_doc_id)
            assert failed_doc is not None and failed_doc.status == DocumentStatus.SUCCEEDED
            assert completed_doc is not None and completed_doc.status == DocumentStatus.SUCCEEDED
            assert failed_doc.error_message is None
            assert completed_doc.error_message is None
        finally:
            session.close()
    finally:
        _cleanup(org.id, user.id)


def test_delete_document_removes_chunks() -> None:
    org, user = _setup_org_user("delete-doc")
    try:
        session = SessionLocal()
        try:
            doc = _create_document(session, org.id, DocumentStatus.SUCCEEDED)
            _create_chunk(session, org.id, doc.id, 0, "chunk one")
            _create_chunk(session, org.id, doc.id, 1, "chunk two")
            session.commit()
            doc_id = doc.id
        finally:
            session.close()

        response = client.delete(
            f"/documents/{doc_id}",
            headers=_auth_headers(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"success": True, "detail": "Document deleted successfully", "status": None}

        session = SessionLocal()
        try:
            doc = session.get(Document, doc_id)
            chunks = (
                session.query(DocumentChunk)
                .filter(DocumentChunk.org_id == org.id, DocumentChunk.doc_id == doc_id)
                .all()
            )
            assert doc is None
            assert chunks == []
        finally:
            session.close()
    finally:
        _cleanup(org.id, user.id)
