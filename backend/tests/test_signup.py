from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.db.models import Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _cleanup(org_id: UUID | None, user_id: UUID | None) -> None:
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


def test_signup_creates_org_and_user() -> None:
    org_id = None
    user_id = None
    password = "TestPass123!"
    payload = {
        "org_name": "Smoke Org",
        "email": f"smoke-{uuid4().hex[:8]}@example.com",
        "password": password,
    }
    try:
        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        assert "access_token" not in body
        assert "refresh_token" not in body
        assert body.get("message") == "Signup successful"
        org_id = UUID(body["org_id"])
        user_id = UUID(body["user_id"])

        session = SessionLocal()
        try:
            org = session.get(Organization, org_id)
            user = session.get(User, user_id)
            assert org is not None
            assert org.name == payload["org_name"]
            assert user is not None
            assert user.email == payload["email"]
            assert user.password_hash is not None
            assert user.password_hash != password
        finally:
            session.close()
    finally:
        _cleanup(org_id, user_id)


def test_signup_duplicate_slug_returns_409() -> None:
    session = SessionLocal()
    org = Organization(name="Slug Org", slug=f"dup-{uuid4().hex[:8]}")
    session.add(org)
    session.commit()
    session.refresh(org)
    try:
        payload = {
            "org_name": "Another Org",
            "org_slug": org.slug,
            "email": f"dup-{uuid4().hex[:8]}@example.com",
            "password": "TestPass123!",
        }
        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 409, response.text
    finally:
        session.delete(org)
        session.commit()
        session.close()


def test_signup_returns_access_token_with_claims() -> None:
    org_id = None
    user_id = None
    payload = {
        "org_name": "Token Org",
        "email": f"token-{uuid4().hex[:8]}@example.com",
        "password": "TestPass123!",
    }
    try:
        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        assert "access_token" not in body
        assert "refresh_token" not in body
        assert body.get("message") == "Signup successful"
        org_id = UUID(body["org_id"])
        user_id = UUID(body["user_id"])
    finally:
        _cleanup(org_id, user_id)
