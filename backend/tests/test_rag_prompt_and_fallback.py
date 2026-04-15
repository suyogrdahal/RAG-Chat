from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import Document, DocumentChunk, OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app
from app.services.prompting import build_rag_prompt, build_retrieved_context

client = TestClient(app)


def _cleanup(org_ids=None, user_ids=None, doc_ids=None, chunk_ids=None) -> None:
    session = SessionLocal()
    try:
        for chunk_id in chunk_ids or []:
            chunk = session.get(DocumentChunk, chunk_id)
            if chunk is not None:
                session.delete(chunk)
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


def _create_org_user(
    *,
    org_name: str = "Needle Org",
    organization_description: str | None = "We help staff with workplace support.",
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


def _create_doc_chunk(org_id: UUID, content: str) -> tuple[Document, DocumentChunk]:
    session = SessionLocal()
    try:
        doc = Document(
            org_id=org_id,
            filename="needle.txt",
            content_type="text/plain",
            size_bytes=len(content),
        )
        session.add(doc)
        session.flush()
        chunk = DocumentChunk(
            org_id=org_id,
            doc_id=doc.id,
            chunk_index=0,
            content=content,
            content_hash=f"hash-{uuid4().hex}",
            embedding=[0.01] * 384,
        )
        session.add(chunk)
        session.commit()
        session.refresh(doc)
        session.refresh(chunk)
        return doc, chunk
    finally:
        session.close()


def _auth_header(user_id: UUID, org_id: UUID) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "org_id": str(org_id), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_greeting_returns_fallback_no_llm_call(monkeypatch) -> None:
    org_id = None
    user_id = None
    called = {"llm": 0}

    async def _llm(*args, **kwargs):
        called["llm"] += 1
        return {"answer": "should-not-be-called", "usage": {}}

    try:
        org, user = _create_org_user(org_name="Greeting Org")
        org_id = org.id
        user_id = user.id
        monkeypatch.setattr("app.services.chat.generate_llm_response", _llm)

        response = client.post(
            "/chat/query",
            json={"query": "Hi"},
            headers=_auth_header(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert called["llm"] == 0
        assert "Greeting Org" in body["answer"]
        assert "ERR1010" not in body["answer"]
        assert body["sources"] == []
        assert body["confidence"] == 0.0
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_low_confidence_returns_fallback_no_llm_call(monkeypatch) -> None:
    org_id = None
    user_id = None
    called = {"llm": 0}

    async def _llm(*args, **kwargs):
        called["llm"] += 1
        return {"answer": "should-not-be-called", "usage": {}}

    async def _search(*args, **kwargs):
        return []

    try:
        org, user = _create_org_user(org_name="LowConf Org")
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _search)
        monkeypatch.setattr("app.services.chat.generate_llm_response", _llm)

        response = client.post(
            "/chat/query",
            json={"query": "What is your reimbursement policy?"},
            headers=_auth_header(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert called["llm"] == 0
        assert body["sources"] == []
        assert body["confidence"] == 0.0
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])


def test_needle_question_answers_from_context(monkeypatch) -> None:
    org_id = None
    user_id = None
    doc_id = None
    chunk_id = None

    async def _search(*args, **kwargs):
        return [
            {
                "chunk_id": str(chunk_id),
                "doc_id": str(doc_id),
                "content": "The office refrigerator code is 1947.",
                "score": 0.99,
            }
        ]

    async def _llm(*args, **kwargs):
        return {"answer": "The office refrigerator code is 1947.", "usage": {}}

    try:
        org, user = _create_org_user(org_name="Needle Org")
        org_id = org.id
        user_id = user.id
        doc, chunk = _create_doc_chunk(org.id, "The office refrigerator code is 1947.")
        doc_id = doc.id
        chunk_id = chunk.id

        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _search)
        monkeypatch.setattr("app.services.chat.generate_llm_response", _llm)

        response = client.post(
            "/chat/query",
            json={"query": "What is the office refrigerator code?"},
            headers=_auth_header(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "1947" in body["answer"]
        assert body["sources"]
        assert body["confidence"] > 0.0
    finally:
        _cleanup(
            org_ids=[org_id] if org_id else [],
            user_ids=[user_id] if user_id else [],
            doc_ids=[doc_id] if doc_id else [],
            chunk_ids=[chunk_id] if chunk_id else [],
        )


def test_prompt_context_is_clean() -> None:
    chunks = [
        {"content": "The office refrigerator code is 1947."},
        {"content": "The support desk is open from 9am to 5pm."},
    ]
    context = build_retrieved_context(chunks=chunks, max_context_chars=1000)
    prompt = build_rag_prompt(
        org_name="Prompt Org",
        org_description="General services.",
        context=context,
        user_query="What is the office refrigerator code?",
    )
    assert "The office refrigerator code is 1947." in prompt
    assert "Project Title" not in prompt
    assert "Deployment:" not in prompt
    assert "Expected Deliverables" not in prompt
    assert "Tech stack" not in prompt


def test_llm_sentinel_triggers_fallback(monkeypatch) -> None:
    org_id = None
    user_id = None

    async def _search(*args, **kwargs):
        return [
            {
                "chunk_id": str(uuid4()),
                "doc_id": str(uuid4()),
                "content": "Needle context exists.",
                "score": 0.95,
            }
        ]

    async def _llm(*args, **kwargs):
        return {"answer": "ERR1010", "usage": {}}

    try:
        org, user = _create_org_user(org_name="Sentinel Org")
        org_id = org.id
        user_id = user.id

        monkeypatch.setattr("app.services.chat.embed_query", lambda text: [0.01] * 384)
        monkeypatch.setattr("app.services.chat.search_similar_chunks", _search)
        monkeypatch.setattr("app.services.chat.generate_llm_response", _llm)

        response = client.post(
            "/chat/query",
            json={"query": "Tell me about the policy."},
            headers=_auth_header(user.id, org.id),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["answer"] != "ERR1010"
        assert "Sentinel Org" in body["answer"]
        assert body["sources"] == []
        assert body["confidence"] == 0.0
    finally:
        _cleanup(org_ids=[org_id] if org_id else [], user_ids=[user_id] if user_id else [])
