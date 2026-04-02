import logging
import asyncio
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.llm.wrapper import generate_llm_response
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


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, response=None):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return self._response


def test_llm_logs_contain_required_fields_and_truncation(caplog, monkeypatch) -> None:
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda timeout=None: _FakeClient(
            response=_FakeResponse(
                {
                    "choices": [{"message": {"content": "A" * 900}}],
                    "usage": {"total_tokens": 12},
                }
            )
        ),
    )

    prompt = "P" * 1200
    query = "what is the summary?"
    request_id = "req-123"
    org_id = str(uuid4())
    user_id = str(uuid4())

    result = asyncio.run(
        generate_llm_response(
            prompt,
            request_id=request_id,
            org_id=org_id,
            user_id=user_id,
            query=query,
        )
    )
    assert result["answer"] == "A" * 900

    events = _event_records(caplog, "llm_response")
    assert events
    payload = events[-1]
    assert payload["request_id"] == request_id
    assert payload["org_id"] == org_id
    assert payload["user_id"] == user_id
    assert payload["query"] == query
    assert isinstance(payload["latency_ms"], int)
    assert len(payload["truncated_prompt"]) == 500
    assert len(payload["truncated_answer"]) == 500


def test_llm_logs_do_not_include_sensitive_fields(caplog, monkeypatch) -> None:
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-api-key")
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda timeout=None: _FakeClient(
            response=_FakeResponse(
                {
                    "choices": [{"message": {"content": "safe answer"}}],
                    "usage": {"total_tokens": 7},
                }
            )
        ),
    )

    prompt = (
        "Authorization: Bearer top.secret.token.value "
        "x" * 300
    )
    asyncio.run(generate_llm_response(prompt, query="q"))

    events = _event_records(caplog, "llm_response")
    assert events
    payload = events[-1]
    assert "full_prompt" not in payload
    assert "embeddings" not in payload
    assert "api_key" not in payload
    assert "authorization" not in payload
    assert "super-secret-api-key" not in caplog.text
