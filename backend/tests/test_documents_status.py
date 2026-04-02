from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _setup_auth_user():
    session = SessionLocal()
    try:
        org = Organization(name="Status Org", slug=f"status-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=f"status-{uuid4().hex[:8]}@example.com",
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


def _upload_doc(org, user):
    response = client.post(
        "/documents/upload",
        headers=_auth_headers(user.id, org.id),
        files={"file": ("sample.txt", b"status test text", "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()["doc_id"]


def test_status_endpoint_requires_auth() -> None:
    response = client.get(f"/documents/{uuid4()}/status")
    assert response.status_code == 401


def test_status_endpoint_scoped_by_org_returns_404_if_other_org() -> None:
    org_a, user_a = _setup_auth_user()
    org_b, user_b = _setup_auth_user()
    try:
        doc_id = _upload_doc(org_a, user_a)
        response = client.get(
            f"/documents/{doc_id}/status",
            headers=_auth_headers(user_b.id, org_b.id),
        )
        assert response.status_code == 404, response.text
    finally:
        _cleanup(org_a.id, user_a.id)
        _cleanup(org_b.id, user_b.id)


def test_status_transitions_on_success() -> None:
    org, user = _setup_auth_user()
    try:
        doc_id = _upload_doc(org, user)
        response = client.get(
            f"/documents/{doc_id}/status",
            headers=_auth_headers(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "succeeded"
        assert payload["error_message"] is None
        assert payload["total_chunks"] >= 0
        assert payload["embedded_chunks"] >= 0
    finally:
        _cleanup(org.id, user.id)


def test_status_sets_failed_on_exception(monkeypatch) -> None:
    org, user = _setup_auth_user()
    try:
        from app.api import documents as documents_api

        def _raise(*args, **kwargs):
            raise RuntimeError("ingestion boom")

        monkeypatch.setattr(documents_api, "_run_ingestion_pipeline", _raise)
        doc_id = _upload_doc(org, user)
        response = client.get(
            f"/documents/{doc_id}/status",
            headers=_auth_headers(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["error_message"] is not None
    finally:
        _cleanup(org.id, user.id)
