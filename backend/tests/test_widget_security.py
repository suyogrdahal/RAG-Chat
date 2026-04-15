import importlib
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

rate_limit_module = importlib.import_module("app.api.deps.rate_limit")
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


class _MockRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.expirations[key] = ttl
        return True


async def _mock_llm_response(*args, **kwargs):
    return {"answer": "ok"}


async def _mock_search_chunks(*args, **kwargs):
    return [{"chunk_id": str(uuid4()), "doc_id": str(uuid4()), "content": "mock context", "score": 0.95}]


def _cleanup(org_ids=None, user_ids=None) -> None:
    session = SessionLocal()
    try:
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


def _create_org_user(
    *,
    allowed_domains: list[str] | None = None,
    max_tokens_per_request: int = 800,
) -> tuple[Organization, User]:
    session = SessionLocal()
    try:
        org = Organization(
            name=f"Widget Org {uuid4().hex[:6]}",
            slug=f"widget-{uuid4().hex[:8]}",
            allowed_domains=allowed_domains or [],
            max_tokens_per_request=max_tokens_per_request,
        )
        session.add(org)
        session.flush()

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
        session.refresh(org)
        session.refresh(user)
        return org, user
    finally:
        session.close()


def _token_for(user: User, org: Organization) -> str:
    return create_access_token(
        {"sub": str(user.id), "org_id": str(org.id), "role": "admin"},
    )


def test_widget_config_requires_auth() -> None:
    response = client.get("/widget/config")
    assert response.status_code == 401


def test_widget_config_returns_public_key_for_org() -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org, user = _create_org_user()
        org_id = org.id
        user_id = user.id
        token = _token_for(user, org)
        response = client.get("/widget/config", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["widget_public_key"] == org.widget_public_key
        assert isinstance(body["allowed_domains"], list)
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_public_chat_with_allowed_origin_succeeds(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org, user = _create_org_user(allowed_domains=["https://example.com"])
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr(
            "app.services.chat.generate_llm_response",
            _mock_llm_response,
        )
        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _mock_search_chunks)
        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: False)
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = client.post(
            "/public/chat/query",
            json={"widget_public_key": org.widget_public_key, "query": "What is the policy?"},
            headers={"Origin": "https://example.com"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["answer"] == "ok"
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_public_chat_with_disallowed_origin_returns_403(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org, user = _create_org_user(allowed_domains=["https://allowed.example"])
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = client.post(
            "/public/chat/query",
            json={"widget_public_key": org.widget_public_key, "query": "Hello"},
            headers={"Origin": "https://blocked.example"},
        )
        assert response.status_code == 403
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_public_chat_with_invalid_widget_public_key_returns_404() -> None:
    response = client.post(
        "/public/chat/query",
        json={"widget_public_key": "invalid-key-value-1234", "query": "Hello"},
        headers={"Origin": "https://example.com"},
    )
    assert response.status_code == 404


def test_public_chat_rate_limit_triggers_429(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    settings = get_settings()
    original_org_limit = settings.public_rate_limit_org_per_min
    original_ip_limit = settings.public_rate_limit_ip_per_min
    try:
        org, user = _create_org_user(allowed_domains=["https://example.com"])
        org_id = org.id
        user_id = user.id

        settings.public_rate_limit_org_per_min = 2
        settings.public_rate_limit_ip_per_min = 10
        monkeypatch.setattr(
            "app.services.chat.generate_llm_response",
            _mock_llm_response,
        )
        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _mock_search_chunks)
        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: False)
        redis = _MockRedis()
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: redis)


        for _ in range(2):
            ok_response = client.post(
                "/public/chat/query",
                json={"widget_public_key": org.widget_public_key, "query": "What is the policy?"},
                headers={"Origin": "https://example.com"},
            )
            assert ok_response.status_code == 200, ok_response.text

        blocked_response = client.post(
            "/public/chat/query",
            json={"widget_public_key": org.widget_public_key, "query": "What is the policy?"},
            headers={"Origin": "https://example.com"},
        )
        assert blocked_response.status_code == 429
    finally:
        settings.public_rate_limit_org_per_min = original_org_limit
        settings.public_rate_limit_ip_per_min = original_ip_limit
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])
