import logging
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
        org = Organization(name="Ingest Log Org", slug=f"ingest-log-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=f"ingest-log-{uuid4().hex[:8]}@example.com",
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


def _event_records(caplog, event_name: str):
    matches = []
    for rec in caplog.records:
        payload = getattr(rec, "payload", None)
        if isinstance(payload, dict) and payload.get("event") == event_name:
            matches.append(payload)
    return matches


def test_ingestion_failed_event_logged(caplog, monkeypatch) -> None:
    caplog.set_level(logging.INFO)
    org, user = _setup_auth_user()
    try:
        from app.api import documents as documents_api

        def _raise(*args, **kwargs):
            raise RuntimeError("secret internal failure payload")

        monkeypatch.setattr(documents_api, "_run_ingestion_pipeline", _raise)

        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("sample.txt", b"safe text", "text/plain")},
        )
        assert response.status_code == 200, response.text
        events = _event_records(caplog, "ingestion_failed")
        assert events
        assert events[-1]["org_id"] == str(org.id)
        assert events[-1]["exception_type"] == "RuntimeError"
    finally:
        _cleanup(org.id, user.id)


def test_no_chunk_content_appears_in_logs(caplog, monkeypatch) -> None:
    caplog.set_level(logging.INFO)
    org, user = _setup_auth_user()
    secret_chunk = "TOP_SECRET_CHUNK_CONTENT_12345"
    try:
        from app.api import documents as documents_api

        def _raise(*args, **kwargs):
            raise RuntimeError(secret_chunk)

        monkeypatch.setattr(documents_api, "_run_ingestion_pipeline", _raise)

        response = client.post(
            "/documents/upload",
            headers=_auth_headers(user.id, org.id),
            files={"file": ("sample.txt", b"safe text", "text/plain")},
        )
        assert response.status_code == 200, response.text
        assert secret_chunk not in caplog.text
    finally:
        _cleanup(org.id, user.id)
