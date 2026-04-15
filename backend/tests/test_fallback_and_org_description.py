import importlib
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

rate_limit_module = importlib.import_module("app.api.deps.rate_limit")
from app.core.security import hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


class _MockRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, ttl: int) -> bool:
        return True


async def _mock_search_chunks_empty(*args, **kwargs):
    return []


async def _mock_search_chunks_good(*args, **kwargs):
    return [
        {
            "chunk_id": str(uuid4()),
            "doc_id": str(uuid4()),
            "content": "Policy: Returns accepted within 30 days with receipt.",
            "score": 0.91,
        }
    ]


async def _mock_llm_err1010(*args, **kwargs):
    return {"answer": "ERR1010"}


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
    org_name: str = "Acme Support",
    organization_description: str | None = None,
) -> tuple[Organization, User]:
    session = SessionLocal()
    try:
        org = Organization(
            name=org_name,
            slug=f"org-{uuid4().hex[:8]}",
            allowed_domains=["https://example.com"],
            organization_description=organization_description,
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


def _post_query(widget_public_key: str, query: str):
    return client.post(
        "/public/chat/query",
        json={"widget_public_key": widget_public_key, "query": query},
        headers={"Origin": "https://example.com"},
    )


def test_greeting_retrieval_empty_triggers_friendly_fallback(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org, user = _create_org_user(org_name="Northwind")
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: True)
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = _post_query(org.widget_public_key, "Hi how are you?")
        assert response.status_code == 200, response.text
        body = response.json()
        assert "ERR1010" not in body["answer"]
        assert "Northwind" in body["answer"]
        assert body["sources"] == []
        assert body["confidence"] == 0.0
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_low_confidence_retrieval_triggers_fallback(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org, user = _create_org_user(org_name="Contoso")
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: False)
        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _mock_search_chunks_empty)
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = _post_query(org.widget_public_key, "What is your exchange policy?")
        assert response.status_code == 200, response.text
        body = response.json()
        assert "ERR1010" not in body["answer"]
        assert "Contoso" in body["answer"]
        assert body["sources"] == []
        assert body["confidence"] == 0.0
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_llm_err1010_triggers_backend_friendly_fallback(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    try:
        org, user = _create_org_user(org_name="Fabrikam")
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: False)
        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _mock_search_chunks_good)
        monkeypatch.setattr("app.services.chat.generate_llm_response", _mock_llm_err1010)
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = _post_query(org.widget_public_key, "Tell me your holiday policy")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["answer"] != "ERR1010"
        assert "Fabrikam" in body["answer"]
        assert body["sources"] == []
        assert body["confidence"] == 0.0
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_fallback_uses_organization_description(monkeypatch) -> None:
    org_id: UUID | None = None
    user_id: UUID | None = None
    description = "We sell sports apparel in Michigan."
    try:
        org, user = _create_org_user(org_name="Samsriti Sports", organization_description=description)
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: True)
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = _post_query(org.widget_public_key, "hello")
        assert response.status_code == 200, response.text
        body = response.json()
        assert "Samsriti Sports" in body["answer"]
        assert description in body["answer"]
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_tenant_isolation_org_scope_unchanged(monkeypatch) -> None:
    org_a_id: UUID | None = None
    user_a_id: UUID | None = None
    org_b_id: UUID | None = None
    user_b_id: UUID | None = None
    captured = {"org_id": None}

    async def _search_with_capture(*, db, org_id, query_embedding, top_k):
        captured["org_id"] = str(org_id)
        return []

    try:
        org_a, user_a = _create_org_user(org_name="Tenant A")
        org_b, user_b = _create_org_user(org_name="Tenant B")
        org_a_id = org_a.id
        user_a_id = user_a.id
        org_b_id = org_b.id
        user_b_id = user_b.id

        monkeypatch.setattr("app.services.chat.is_greeting", lambda q: False)
        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _search_with_capture)
        monkeypatch.setattr(rate_limit_module.time, "time", lambda: 1_700_000_000)
        monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: _MockRedis())

        response = _post_query(org_a.widget_public_key, "What docs do you have?")
        assert response.status_code == 200, response.text
        assert captured["org_id"] == str(org_a.id)
        assert captured["org_id"] != str(org_b.id)
    finally:
        _cleanup(
            org_ids=[i for i in [org_a_id, org_b_id] if i],
            user_ids=[i for i in [user_a_id, user_b_id] if i],
        )
