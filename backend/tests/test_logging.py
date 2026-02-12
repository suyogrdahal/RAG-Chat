import logging
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


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


def _create_login_user(password: str = "TestPass123!"):
    session = SessionLocal()
    try:
        org = Organization(name="Log Org", slug=f"log-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=f"log-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password(password),
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


def _event_records(caplog, event_name: str):
    matches = []
    for rec in caplog.records:
        payload = getattr(rec, "payload", None)
        if isinstance(payload, dict) and payload.get("event") == event_name:
            matches.append(payload)
    return matches


def test_x_request_id_header_present() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_authorization_header_never_logged(caplog) -> None:
    caplog.set_level(logging.INFO)
    secret = "Bearer super.secret.token"
    response = client.get("/auth/whoami", headers={"Authorization": secret})
    assert response.status_code == 401
    assert "super.secret.token" not in caplog.text
    assert secret not in caplog.text


def test_login_failure_logs_auth_login_failure(caplog) -> None:
    caplog.set_level(logging.INFO)
    org, user = _create_login_user()
    try:
        response = client.post(
            "/auth/login",
            json={
                "org_slug": org.slug,
                "email": user.email,
                "password": "WrongPass123!",
            },
            headers={"User-Agent": "pytest-agent"},
        )
        assert response.status_code == 401
        events = _event_records(caplog, "auth_login_failure")
        assert events
        assert events[-1]["reason"] == "invalid_credentials"
    finally:
        _cleanup(org.id, user.id)


def test_login_success_logs_auth_login_success(caplog) -> None:
    caplog.set_level(logging.INFO)
    org, user = _create_login_user()
    try:
        response = client.post(
            "/auth/login",
            json={
                "org_slug": org.slug,
                "email": user.email,
                "password": "TestPass123!",
            },
            headers={"User-Agent": "pytest-agent"},
        )
        assert response.status_code == 200
        events = _event_records(caplog, "auth_login_success")
        assert events
        assert events[-1]["user_id"] == str(user.id)
        assert events[-1]["org_id"] == str(org.id)
    finally:
        _cleanup(org.id, user.id)


def test_refresh_failure_logs_auth_refresh_failure(caplog) -> None:
    caplog.set_level(logging.INFO)
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-refresh-token"},
    )
    assert response.status_code == 401
    events = _event_records(caplog, "auth_refresh_failure")
    assert events
