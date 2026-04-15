from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import Document, DocumentChunk, DocumentStatus, OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _cleanup(org_ids=None, user_ids=None, doc_ids=None) -> None:
    session = SessionLocal()
    try:
        for doc_id in doc_ids or []:
            doc = session.get(Document, doc_id)
            if doc is not None:
                session.delete(doc)
        for user_id in user_ids or []:
            user = session.get(User, user_id)
            if user is not None:
                session.delete(user)
        for org_id in org_ids or []:
            org = session.get(Organization, org_id)
            if org is not None:
                session.delete(org)
        session.commit()
    finally:
        session.close()


def _create_org(session, prefix: str) -> Organization:
    org = Organization(name=f"{prefix} Org", slug=f"{prefix}-{uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _create_user(session, org_id) -> User:
    user = User(
        org_id=org_id,
        active_org_id=org_id,
        email=f"user-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
        role="admin",
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def _create_document(session, org_id, name: str, status: DocumentStatus) -> Document:
    doc = Document(
        org_id=org_id,
        filename=name,
        content_type="text/plain",
        size_bytes=100,
        status=status,
        error_message="failed" if status == DocumentStatus.FAILED else None,
    )
    session.add(doc)
    session.flush()
    return doc


def _create_chunk(session, org_id, doc_id, chunk_index: int) -> None:
    vector = [0.0] * 384
    vector[0] = float(chunk_index + 1)
    session.add(
        DocumentChunk(
            org_id=org_id,
            doc_id=doc_id,
            chunk_index=chunk_index,
            content=f"chunk-{chunk_index}",
            content_hash=f"hash-{uuid4().hex}",
            embedding=vector,
        )
    )
    session.flush()


def _auth_headers(user_id, org_id) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "org_id": str(org_id), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_counts_correctly() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org = _create_org(session, "dash")
        org_ids = [org.id]
        user = _create_user(session, org.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
        session.commit()

        doc_completed = _create_document(session, org.id, "a.txt", DocumentStatus.SUCCEEDED)
        doc_processing = _create_document(session, org.id, "b.txt", DocumentStatus.PROCESSING)
        doc_failed = _create_document(session, org.id, "c.txt", DocumentStatus.FAILED)
        doc_ids = [doc_completed.id, doc_processing.id, doc_failed.id]
        _create_chunk(session, org.id, doc_completed.id, 0)
        _create_chunk(session, org.id, doc_completed.id, 1)
        _create_chunk(session, org.id, doc_processing.id, 0)
        session.commit()

        response = client.get("/dashboard", headers=_auth_headers(user.id, org.id))
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total_documents"] == 3
        assert payload["documents_completed"] == 1
        assert payload["documents_processing"] == 1
        assert payload["documents_failed"] == 1
        assert payload["total_chunks"] == 3
        assert payload["total_tokens_used"] == 0
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)


def test_org_isolation_dashboard() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org_a = _create_org(session, "orga")
        org_b = _create_org(session, "orgb")
        org_ids = [org_a.id, org_b.id]
        user = _create_user(session, org_a.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org_a.id, role="admin"))
        session.commit()

        doc_a = _create_document(session, org_a.id, "a.txt", DocumentStatus.SUCCEEDED)
        doc_b = _create_document(session, org_b.id, "b.txt", DocumentStatus.FAILED)
        doc_ids = [doc_a.id, doc_b.id]
        _create_chunk(session, org_a.id, doc_a.id, 0)
        _create_chunk(session, org_b.id, doc_b.id, 0)
        session.commit()

        response = client.get("/dashboard", headers=_auth_headers(user.id, org_a.id))
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["total_documents"] == 1
        assert payload["documents_completed"] == 1
        assert payload["documents_processing"] == 0
        assert payload["documents_failed"] == 0
        assert payload["total_chunks"] == 1
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)
