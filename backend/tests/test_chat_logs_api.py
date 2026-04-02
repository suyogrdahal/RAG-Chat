from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import ChatLog, OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app
from app.repositories.chat_logs import ChatLogsRepository

client = TestClient(app)


def _create_org(session) -> Organization:
    org = Organization(
        name=f"Chat Logs Org {uuid4().hex[:8]}",
        slug=f"chat-logs-{uuid4().hex[:8]}",
        allowed_domains=[],
    )
    session.add(org)
    session.flush()
    return org


def _create_user(session, org: Organization) -> User:
    user = User(
        org_id=org.id,
        active_org_id=org.id,
        email=f"user-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
        role="admin",
        is_active=True,
    )
    session.add(user)
    session.flush()
    session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
    session.commit()
    return user


def _create_chat_log(
    *,
    org_id: UUID,
    query_text: str,
    response_text: str,
    confidence: float | None = 0.71,
    session_id: str | None = None,
    sources_json: list[dict] | None = None,
) -> UUID:
    session = SessionLocal()
    try:
        log = ChatLog(
            org_id=org_id,
            session_id=session_id,
            query_text=query_text,
            response_text=response_text,
            confidence=confidence,
            sources_json=sources_json,
        )
        session.add(log)
        session.commit()
        return log.id
    finally:
        session.close()


def _cleanup(
    *,
    org_ids: list[UUID] | None = None,
    user_ids: list[UUID] | None = None,
    log_ids: list[UUID] | None = None,
) -> None:
    session = SessionLocal()
    try:
        for log_id in log_ids or []:
            log = session.get(ChatLog, log_id)
            if log is not None:
                session.delete(log)
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


def _auth_headers(user_id: UUID, org_id: UUID) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "org_id": str(org_id), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_chat_query_creates_chat_log(monkeypatch) -> None:
    session = SessionLocal()
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org = _create_org(session)
        org_id = org.id
        user = _create_user(session, org)
        user_id = user.id

        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: True)

        response = client.post(
            "/chat/query",
            headers=_auth_headers(user_id, org_id),
            json={"query": "hello"},
        )
        assert response.status_code == 200, response.text

        verify = SessionLocal()
        try:
            rows = (
                verify.query(ChatLog)
                .filter(ChatLog.org_id == org_id)
                .order_by(ChatLog.created_at.desc())
                .all()
            )
            assert len(rows) == 1
            assert rows[0].query_text == "hello"
            assert rows[0].response_text.lower().startswith("hi im chat assisant of")
            assert rows[0].user_id == user_id
        finally:
            verify.close()
    finally:
        session.close()
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_chat_logs_requires_auth() -> None:
    response = client.get("/chat-logs")
    assert response.status_code == 401


def test_chat_logs_returns_only_current_org_logs() -> None:
    session = SessionLocal()
    org_a_id: UUID | None = None
    org_b_id: UUID | None = None
    user_a_id: UUID | None = None
    try:
        org_a = _create_org(session)
        org_b = _create_org(session)
        user_a = _create_user(session, org_a)
        org_a_id = org_a.id
        org_b_id = org_b.id
        user_a_id = user_a.id

        own_log = _create_chat_log(org_id=org_a.id, query_text="own org query", response_text="own response")
        _create_chat_log(org_id=org_b.id, query_text="other org query", response_text="other response")

        response = client.get("/chat-logs", headers=_auth_headers(user_a_id, org_a_id))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == str(own_log)
        assert body["items"][0]["query_text"] == "own org query"
    finally:
        session.close()
        _cleanup(org_ids=[i for i in [org_a_id, org_b_id] if i], user_ids=[user_a_id] if user_a_id else [])


def test_chat_log_detail_other_org_returns_404() -> None:
    session = SessionLocal()
    org_a_id: UUID | None = None
    org_b_id: UUID | None = None
    user_a_id: UUID | None = None
    foreign_log_id: UUID | None = None
    try:
        org_a = _create_org(session)
        org_b = _create_org(session)
        user_a = _create_user(session, org_a)
        org_a_id = org_a.id
        org_b_id = org_b.id
        user_a_id = user_a.id
        foreign_log_id = _create_chat_log(
            org_id=org_b.id,
            query_text="other org query",
            response_text="other org response",
        )

        response = client.get(
            f"/chat-logs/{foreign_log_id}",
            headers=_auth_headers(user_a_id, org_a_id),
        )
        assert response.status_code == 404
    finally:
        session.close()
        _cleanup(
            org_ids=[i for i in [org_a_id, org_b_id] if i],
            user_ids=[user_a_id] if user_a_id else [],
            log_ids=[i for i in [foreign_log_id] if i],
        )


def test_chat_logs_search_filter() -> None:
    session = SessionLocal()
    org_id: UUID | None = None
    user_id: UUID | None = None
    log_ids: list[UUID] = []
    try:
        org = _create_org(session)
        org_id = org.id
        user = _create_user(session, org)
        user_id = user.id

        log_ids.append(_create_chat_log(org_id=org.id, query_text="account reset policy", response_text="policy answer"))
        log_ids.append(
            _create_chat_log(org_id=org.id, query_text="billing process", response_text="billing answer")
        )

        response = client.get(
            "/chat-logs?search=policy",
            headers=_auth_headers(user_id, org_id),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert "policy" in body["items"][0]["query_text"]
    finally:
        session.close()
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [], log_ids=log_ids)


def test_chat_logs_pagination() -> None:
    session = SessionLocal()
    org_id: UUID | None = None
    user_id: UUID | None = None
    log_ids: list[UUID] = []
    try:
        org = _create_org(session)
        org_id = org.id
        user = _create_user(session, org)
        user_id = user.id

        log_ids.extend(
            [
                _create_chat_log(
                    org_id=org.id,
                    query_text=f"q{i}",
                    response_text=f"r{i}",
                    session_id=f"session-{i}",
                )
                for i in range(3)
            ]
        )

        response = client.get("/chat-logs?limit=2&offset=1", headers=_auth_headers(user_id, org_id))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert body["total"] == 3
        assert len(body["items"]) == 2
    finally:
        session.close()
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [], log_ids=log_ids)


def test_chat_insert_failure_does_not_break_response(monkeypatch) -> None:
    session = SessionLocal()
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org = _create_org(session)
        org_id = org.id
        user = _create_user(session, org)
        user_id = user.id

        def _raise(*args, **kwargs):
            raise RuntimeError("intentional insert failure")

        monkeypatch.setattr(ChatLogsRepository, "create_chat_log", _raise)
        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: True)

        response = client.post(
            "/chat/query",
            headers=_auth_headers(user_id, org_id),
            json={"query": "hello"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["answer"].lower().startswith("hi im chat assisant of")

        verify = SessionLocal()
        try:
            assert (
                verify.query(ChatLog)
                .filter(ChatLog.org_id == org_id)
                .count()
                == 0
            )
        finally:
            verify.close()
    finally:
        session.close()
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])
