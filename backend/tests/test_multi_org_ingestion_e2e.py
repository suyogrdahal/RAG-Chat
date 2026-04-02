from pathlib import Path
from shutil import rmtree
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import Document, DocumentChunk, OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.ingestion.parsers import ParsedText
from app.main import app
from app.repositories.vector_repository import VectorRepository

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


def test_multi_org_ingestion_pdf_txt_and_isolation(monkeypatch) -> None:
    org_a, user_a = _setup_org_user("orga")
    org_b, user_b = _setup_org_user("orgb")
    try:
        from app.api import documents as documents_api

        def _fake_parse_pdf(_bytes: bytes) -> ParsedText:
            return ParsedText(text="pdf content for org b", page_count=1)

        def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
            return [[0.01] * 384 for _ in texts]

        monkeypatch.setattr(documents_api, "parse_pdf", _fake_parse_pdf)
        monkeypatch.setattr(documents_api, "embed_texts", _fake_embed_texts)

        upload_a = client.post(
            "/documents/upload",
            headers=_auth_headers(user_a.id, org_a.id),
            files={"file": ("a.txt", b"txt content for org a", "text/plain")},
        )
        assert upload_a.status_code == 200, upload_a.text
        doc_a_id = UUID(upload_a.json()["doc_id"])

        upload_b = client.post(
            "/documents/upload",
            headers=_auth_headers(user_b.id, org_b.id),
            files={"file": ("b.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert upload_b.status_code == 200, upload_b.text
        doc_b_id = UUID(upload_b.json()["doc_id"])

        session = SessionLocal()
        try:
            doc_a = session.get(Document, doc_a_id)
            doc_b = session.get(Document, doc_b_id)
            assert doc_a is not None and doc_b is not None
            assert str(doc_a.org_id) == str(org_a.id)
            assert str(doc_b.org_id) == str(org_b.id)
            assert doc_a.status.value == "succeeded"
            assert doc_b.status.value == "succeeded"

            chunks_a = (
                session.query(DocumentChunk)
                .filter(DocumentChunk.org_id == org_a.id, DocumentChunk.doc_id == doc_a.id)
                .all()
            )
            chunks_b = (
                session.query(DocumentChunk)
                .filter(DocumentChunk.org_id == org_b.id, DocumentChunk.doc_id == doc_b.id)
                .all()
            )
            assert chunks_a
            assert chunks_b
            assert all(str(c.org_id) == str(org_a.id) for c in chunks_a)
            assert all(str(c.org_id) == str(org_b.id) for c in chunks_b)

            repo = VectorRepository(session)
            result_a = repo.similarity_search(
                org_id=org_a.id,
                query_embedding=[0.01] * 384,
                top_k=10,
            )
            assert result_a
            assert all(str(row["org_id"]) == str(org_a.id) for row in result_a)

            guessed_cross = repo.similarity_search(
                org_id=org_a.id,
                query_embedding=[0.01] * 384,
                top_k=10,
                doc_id=doc_b.id,
            )
            assert guessed_cross == []
        finally:
            session.close()

        cross_status = client.get(
            f"/documents/{doc_a_id}/status",
            headers=_auth_headers(user_b.id, org_b.id),
        )
        assert cross_status.status_code == 404, cross_status.text
    finally:
        _cleanup(org_a.id, user_a.id)
        _cleanup(org_b.id, user_b.id)


def test_failure_case_marks_only_that_org_doc_failed(monkeypatch) -> None:
    org_a, user_a = _setup_org_user("faila")
    org_b, user_b = _setup_org_user("failb")
    try:
        from app.api import documents as documents_api

        def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
            joined = " ".join(texts)
            if "FAIL_MARKER" in joined:
                raise RuntimeError("embedding failure")
            return [[0.02] * 384 for _ in texts]

        monkeypatch.setattr(documents_api, "embed_texts", _fake_embed_texts)

        ok_upload = client.post(
            "/documents/upload",
            headers=_auth_headers(user_a.id, org_a.id),
            files={"file": ("ok.txt", b"normal content", "text/plain")},
        )
        assert ok_upload.status_code == 200, ok_upload.text
        ok_doc_id = UUID(ok_upload.json()["doc_id"])

        fail_upload = client.post(
            "/documents/upload",
            headers=_auth_headers(user_b.id, org_b.id),
            files={"file": ("fail.txt", b"FAIL_MARKER content", "text/plain")},
        )
        assert fail_upload.status_code == 200, fail_upload.text
        fail_doc_id = UUID(fail_upload.json()["doc_id"])

        session = SessionLocal()
        try:
            ok_doc = session.get(Document, ok_doc_id)
            fail_doc = session.get(Document, fail_doc_id)
            assert ok_doc is not None and fail_doc is not None
            assert ok_doc.status.value == "succeeded"
            assert fail_doc.status.value == "failed"
            assert fail_doc.error_message is not None
        finally:
            session.close()
    finally:
        _cleanup(org_a.id, user_a.id)
        _cleanup(org_b.id, user_b.id)
