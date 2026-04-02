from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.models import Document, OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _setup_auth_user():
    session = SessionLocal()
    try:
        org = Organization(name="Docs Org", slug=f"docs-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=f"docs-{uuid4().hex[:8]}@example.com",
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


def test_upload_pdf_ok() -> None:
    org, user = _setup_auth_user()
    try:
        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("sample.pdf", b"%PDF-1.4\nhello", "application/pdf")},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] in {"queued", "processing"}

        session = SessionLocal()
        try:
            doc = session.get(Document, payload["doc_id"])
            assert doc is not None
            assert str(doc.org_id) == str(org.id)
            assert doc.content_type == "application/pdf"
        finally:
            session.close()
    finally:
        _cleanup(org.id, user.id)


def test_upload_txt_ok() -> None:
    org, user = _setup_auth_user()
    try:
        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("sample.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] in {"queued", "processing"}
    finally:
        _cleanup(org.id, user.id)


def test_upload_rejects_large_file() -> None:
    org, user = _setup_auth_user()
    settings = get_settings()
    old_limit = settings.max_upload_mb
    settings.max_upload_mb = 1
    try:
        large = b"x" * (1024 * 1024 + 1)
        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("large.txt", large, "text/plain")},
        )
        assert response.status_code == 413, response.text
    finally:
        settings.max_upload_mb = old_limit
        _cleanup(org.id, user.id)


def test_upload_large_file_returns_413() -> None:
    org, user = _setup_auth_user()
    settings = get_settings()
    old_limit = settings.max_upload_mb
    settings.max_upload_mb = 1
    try:
        large = b"x" * (1024 * 1024 + 1)
        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("large.txt", large, "text/plain")},
        )
        assert response.status_code == 413, response.text
    finally:
        settings.max_upload_mb = old_limit
        _cleanup(org.id, user.id)


def test_upload_rejects_unsupported_type() -> None:
    org, user = _setup_auth_user()
    try:
        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("sample.png", b"pngdata", "image/png")},
        )
        assert response.status_code == 415, response.text
    finally:
        _cleanup(org.id, user.id)


def test_upload_requires_auth() -> None:
    response = client.post(
        "/documents/upload",
        files={"file": ("sample.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 401


def test_huge_extracted_text_marks_failed() -> None:
    org, user = _setup_auth_user()
    settings = get_settings()
    old_text_limit = settings.max_text_chars
    old_upload_limit = settings.max_upload_mb
    settings.max_text_chars = 100
    settings.max_upload_mb = 5
    try:
        payload = ("too big text " * 40).encode("utf-8")
        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("huge.txt", payload, "text/plain")},
        )
        assert response.status_code == 200, response.text
        doc_id = response.json()["doc_id"]

        status_response = client.get(
            f"/documents/{doc_id}/status",
            headers=_auth_headers(user.id, org.id),
        )
        assert status_response.status_code == 200, status_response.text
        status_payload = status_response.json()
        assert status_payload["status"] == "failed"
        assert status_payload["error_message"] == "Extracted text exceeds allowed size"
    finally:
        settings.max_text_chars = old_text_limit
        settings.max_upload_mb = old_upload_limit
        _cleanup(org.id, user.id)
