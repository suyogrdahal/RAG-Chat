from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import Document, DocumentStatus, OrgMembership, Organization, User
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


def _create_org(session, name_prefix: str) -> Organization:
    org = Organization(name=f"{name_prefix} Org", slug=f"{name_prefix}-{uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _create_user(session, org_id: UUID, active_org_id: UUID | None = None) -> User:
    user = User(
        org_id=org_id,
        active_org_id=active_org_id,
        email=f"user-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
        role="admin",
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def _create_doc(session, org_id: UUID, name: str, status: DocumentStatus) -> Document:
    doc = Document(
        org_id=org_id,
        filename=name,
        content_type="text/plain",
        size_bytes=42,
        status=status,
        error_message="boom" if status == DocumentStatus.FAILED else None,
    )
    session.add(doc)
    session.flush()
    return doc


def test_list_documents_requires_auth() -> None:
    response = client.get("/documents")
    assert response.status_code == 401


def test_list_documents_scoped_by_org() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org_a = _create_org(session, "a")
        org_b = _create_org(session, "b")
        org_ids = [org_a.id, org_b.id]
        user = _create_user(session, org_id=org_a.id, active_org_id=org_a.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org_a.id, role="admin"))
        session.commit()

        doc_a = _create_doc(session, org_a.id, "a.txt", DocumentStatus.QUEUED)
        doc_b = _create_doc(session, org_b.id, "b.txt", DocumentStatus.QUEUED)
        doc_ids = [doc_a.id, doc_b.id]
        session.commit()

        token = create_access_token({"sub": str(user.id), "org_id": str(org_a.id), "role": "admin"})
        response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == str(doc_a.id)
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)


def test_list_documents_status_filter() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org = _create_org(session, "status")
        org_ids = [org.id]
        user = _create_user(session, org_id=org.id, active_org_id=org.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
        session.commit()

        doc_q = _create_doc(session, org.id, "queued.txt", DocumentStatus.QUEUED)
        doc_s = _create_doc(session, org.id, "done.txt", DocumentStatus.SUCCEEDED)
        doc_ids = [doc_q.id, doc_s.id]
        session.commit()

        token = create_access_token({"sub": str(user.id), "org_id": str(org.id), "role": "admin"})
        response = client.get(
            "/documents?status=succeeded",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == str(doc_s.id)
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)


def test_list_documents_pagination() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org = _create_org(session, "page")
        org_ids = [org.id]
        user = _create_user(session, org_id=org.id, active_org_id=org.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
        session.commit()

        docs = [
            _create_doc(session, org.id, f"doc-{i}.txt", DocumentStatus.QUEUED)
            for i in range(3)
        ]
        doc_ids = [d.id for d in docs]
        session.commit()

        token = create_access_token({"sub": str(user.id), "org_id": str(org.id), "role": "admin"})
        response = client.get(
            "/documents?limit=2&offset=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert body["total"] == 3
        assert len(body["items"]) == 2
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)


def test_get_document_same_org() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org = _create_org(session, "get")
        org_ids = [org.id]
        user = _create_user(session, org_id=org.id, active_org_id=org.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
        session.commit()

        doc = _create_doc(session, org.id, "doc.txt", DocumentStatus.PROCESSING)
        doc_ids = [doc.id]
        session.commit()

        token = create_access_token({"sub": str(user.id), "org_id": str(org.id), "role": "admin"})
        response = client.get(
            f"/documents/{doc.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(doc.id)
        assert body["status"] == "processing"
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)


def test_get_document_other_org_returns_404() -> None:
    session = SessionLocal()
    org_ids = []
    user_ids = []
    doc_ids = []
    try:
        org_a = _create_org(session, "x")
        org_b = _create_org(session, "y")
        org_ids = [org_a.id, org_b.id]
        user = _create_user(session, org_id=org_a.id, active_org_id=org_a.id)
        user_ids = [user.id]
        session.add(OrgMembership(user_id=user.id, org_id=org_a.id, role="admin"))
        session.commit()

        doc = _create_doc(session, org_b.id, "secret.txt", DocumentStatus.QUEUED)
        doc_ids = [doc.id]
        session.commit()

        token = create_access_token({"sub": str(user.id), "org_id": str(org_a.id), "role": "admin"})
        response = client.get(
            f"/documents/{doc.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        session.close()
        _cleanup(org_ids=org_ids, user_ids=user_ids, doc_ids=doc_ids)
