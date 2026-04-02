from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import OrgMembership, Organization, RefreshToken, User
from app.db.session import SessionLocal
from app.main import app


client = TestClient(app)


def test_password_hashing_ok() -> None:
    hashed = hash_password("TestPass123!")
    assert verify_password("TestPass123!", hashed) is True
    assert verify_password("WrongPass", hashed) is False


def test_whoami_requires_auth() -> None:
    response = client.get("/auth/whoami")
    assert response.status_code == 401


def test_whoami_rejects_invalid_token() -> None:
    response = client.get(
        "/auth/whoami",
        headers={"Authorization": "Bearer not-a-token"},
    )
    assert response.status_code == 401


def test_whoami_accepts_valid_token() -> None:
    org_id = None
    user_id = None
    session = SessionLocal()
    try:
        org = Organization(name="Whoami Org", slug=f"whoami-{uuid4().hex[:8]}")
        session.add(org)
        session.flush()
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=f"whoami-{uuid4().hex[:8]}@example.com",
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
        org_id = org.id
        user_id = user.id

        token = create_access_token(
            {
                "sub": str(user.id),
                "org_id": str(org.id),
                "role": "admin",
            },
            expires_minutes=5,
        )
        response = client.get(
            "/auth/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == str(UUID(str(user.id)))
        assert payload["org_id"] == str(UUID(str(org.id)))
        assert payload["role"] == "admin"
    finally:
        session.close()
        _cleanup(org_id, user_id)


def test_whoami_rejects_expired_token() -> None:
    token = create_access_token(
        {
            "sub": "55555555-5555-5555-5555-555555555555",
            "org_id": "66666666-6666-6666-6666-666666666666",
            "role": "admin",
        },
        expires_minutes=-1,
    )
    response = client.get(
        "/auth/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def _cleanup(org_id, user_id) -> None:
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


def _create_org_and_user(password: str = "TestPass123!", is_active: bool = True):
    session = SessionLocal()
    org = Organization(name="Auth Org", slug=f"auth-{uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    user = User(
        org_id=org.id,
        active_org_id=org.id,
        email=f"user-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(password),
        role="admin",
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    session.add(OrgMembership(user_id=user.id, org_id=org.id, role="admin"))
    session.commit()
    session.refresh(org)
    session.refresh(user)
    session.close()
    return org, user


def _active_refresh_tokens_count(user_id) -> int:
    session = SessionLocal()
    try:
        return (
            session.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .count()
        )
    finally:
        session.close()


def test_login_success_returns_access_token_and_updates_last_login() -> None:
    org_id = None
    user_id = None
    password = "TestPass123!"
    try:
        org, user = _create_org_and_user(password=password, is_active=True)
        org_id = org.id
        user_id = user.id

        response = client.post(
            "/auth/login",
            json={
                "email": user.email,
                "password": password,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["org_id"] == str(org.id)
        assert body["user_id"] == str(user.id)
        claims = decode_access_token(body["access_token"])
        assert claims["sub"] == str(user.id)
        assert claims["org_id"] == str(org.id)
        assert claims["role"] == "admin"
        assert body["refresh_token"]

        session = SessionLocal()
        try:
            refresh = session.query(RefreshToken).filter(RefreshToken.user_id == user.id).one()
            assert refresh.token_hash == hash_refresh_token(body["refresh_token"])
        finally:
            session.close()

        session = SessionLocal()
        session.expire_all()
        saved_user = session.get(User, user.id)
        assert saved_user is not None
        assert saved_user.last_login_at is not None
    finally:
        if "session" in locals():
            session.close()
        _cleanup(org_id, user_id)


def test_login_rejects_invalid_password() -> None:
    org_id = None
    user_id = None
    try:
        org, user = _create_org_and_user(password="TestPass123!", is_active=True)
        org_id = org.id
        user_id = user.id

        response = client.post(
            "/auth/login",
            json={
                "org_slug": org.slug,
                "email": user.email,
                "password": "WrongPass123!",
            },
        )
        assert response.status_code == 401, response.text
    finally:
        _cleanup(org_id, user_id)


def test_login_rejects_inactive_user() -> None:
    org_id = None
    user_id = None
    try:
        org, user = _create_org_and_user(password="TestPass123!", is_active=False)
        org_id = org.id
        user_id = user.id

        response = client.post(
            "/auth/login",
            json={
                "org_slug": org.slug,
                "email": user.email,
                "password": "TestPass123!",
            },
        )
        assert response.status_code == 401, response.text
    finally:
        _cleanup(org_id, user_id)


def test_refresh_success_rotates_token_and_returns_new_access() -> None:
    org_id = None
    user_id = None
    try:
        org, user = _create_org_and_user()
        org_id = org.id
        user_id = user.id
        login_response = client.post(
            "/auth/login",
            json={"org_slug": org.slug, "email": user.email, "password": "TestPass123!"},
        )
        assert login_response.status_code == 200, login_response.text
        old_refresh = login_response.json()["refresh_token"]

        response = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["refresh_token"] != old_refresh
        claims = decode_access_token(body["access_token"])
        assert claims["sub"] == str(user.id)
        assert claims["org_id"] == str(org.id)
        assert claims["role"] == "admin"

        session = SessionLocal()
        try:
            old_row = (
                session.query(RefreshToken)
                .filter(RefreshToken.token_hash == hash_refresh_token(old_refresh))
                .one()
            )
            new_row = (
                session.query(RefreshToken)
                .filter(RefreshToken.token_hash == hash_refresh_token(body["refresh_token"]))
                .one()
            )
            assert old_row.revoked_at is not None
            assert old_row.rotated_to_token_id == new_row.id
            assert new_row.revoked_at is None
        finally:
            session.close()
    finally:
        _cleanup(org_id, user_id)


def test_refresh_rejects_invalid_token() -> None:
    response = client.post("/auth/refresh", json={"refresh_token": "not-valid-token-value"})
    assert response.status_code == 401, response.text


def test_refresh_rejects_expired_token() -> None:
    org_id = None
    user_id = None
    session = SessionLocal()
    try:
        org, user = _create_org_and_user()
        org_id = org.id
        user_id = user.id
        raw = create_refresh_token_value()
        expired = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            created_at=datetime.now(timezone.utc) - timedelta(days=20),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        session.add(expired)
        session.commit()
        session.refresh(expired)

        response = client.post("/auth/refresh", json={"refresh_token": raw})
        assert response.status_code == 401, response.text
    finally:
        session.close()
        _cleanup(org_id, user_id)


def test_refresh_rejects_revoked_token() -> None:
    org_id = None
    user_id = None
    session = SessionLocal()
    try:
        org, user = _create_org_and_user()
        org_id = org.id
        user_id = user.id
        raw = create_refresh_token_value()
        revoked = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=14),
            revoked_at=datetime.now(timezone.utc),
        )
        session.add(revoked)
        session.commit()

        response = client.post("/auth/refresh", json={"refresh_token": raw})
        assert response.status_code == 401, response.text
    finally:
        session.close()
        _cleanup(org_id, user_id)


def test_refresh_reuse_detection_revokes_all_user_tokens() -> None:
    org_id = None
    user_id = None
    try:
        org, user = _create_org_and_user()
        org_id = org.id
        user_id = user.id
        login_response = client.post(
            "/auth/login",
            json={"org_slug": org.slug, "email": user.email, "password": "TestPass123!"},
        )
        assert login_response.status_code == 200, login_response.text
        first_refresh = login_response.json()["refresh_token"]

        rotate_response = client.post(
            "/auth/refresh", json={"refresh_token": first_refresh}
        )
        assert rotate_response.status_code == 200, rotate_response.text
        assert _active_refresh_tokens_count(user.id) == 1

        reuse_response = client.post(
            "/auth/refresh", json={"refresh_token": first_refresh}
        )
        assert reuse_response.status_code == 401, reuse_response.text
        assert _active_refresh_tokens_count(user.id) == 0
    finally:
        _cleanup(org_id, user_id)


def test_refresh_reuse_detection_revokes_all_user_() -> None:
    test_refresh_reuse_detection_revokes_all_user_tokens()
