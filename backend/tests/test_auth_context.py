from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _cleanup(user_id=None, org_ids=None) -> None:
    session = SessionLocal()
    try:
        if user_id is not None:
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


def _create_org(session, name_prefix: str) -> Organization:
    org = Organization(name=f"{name_prefix} Org", slug=f"{name_prefix}-{uuid4().hex[:8]}")
    session.add(org)
    session.flush()
    return org


def _create_user(session, org_id, active_org_id=None, is_active=True) -> User:
    user = User(
        org_id=org_id,
        active_org_id=active_org_id,
        email=f"user-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123!"),
        role="admin",
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def test_get_current_user_missing_token_returns_401() -> None:
    response = client.get("/auth/whoami")
    assert response.status_code == 401


def test_get_current_user_invalid_token_returns_401() -> None:
    response = client.get(
        "/auth/whoami",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_get_current_user_valid_token_user_missing_returns_401() -> None:
    token = create_access_token({"sub": str(uuid4()), "org_id": str(uuid4()), "role": "admin"})
    response = client.get(
        "/auth/whoami",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_require_org_token_org_not_member_returns_403() -> None:
    user_id = None
    org_ids = []
    session = SessionLocal()
    try:
        org_a = _create_org(session, "a")
        org_b = _create_org(session, "b")
        org_ids = [org_a.id, org_b.id]
        user = _create_user(session, org_id=org_a.id, active_org_id=org_a.id)
        user_id = user.id
        session.add(OrgMembership(user_id=user.id, org_id=org_a.id, role="admin"))
        session.commit()

        token = create_access_token(
            {"sub": str(user.id), "org_id": str(org_b.id), "role": "admin"}
        )
        response = client.get(
            "/auth/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
    finally:
        session.close()
        _cleanup(user_id=user_id, org_ids=org_ids)


def test_require_org_token_without_org_uses_active_org_id() -> None:
    user_id = None
    org_ids = []
    session = SessionLocal()
    try:
        org = _create_org(session, "active")
        org_ids = [org.id]
        user = _create_user(session, org_id=org.id, active_org_id=org.id)
        user_id = user.id
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="editor"))
        session.commit()

        token = create_access_token({"sub": str(user.id)})
        response = client.get(
            "/auth/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == str(user.id)
        assert body["org_id"] == str(org.id)
        assert body["role"] == "editor"
    finally:
        session.close()
        _cleanup(user_id=user_id, org_ids=org_ids)


def test_require_org_token_without_org_single_membership_resolves() -> None:
    user_id = None
    org_ids = []
    session = SessionLocal()
    try:
        org = _create_org(session, "single")
        org_ids = [org.id]
        user = _create_user(session, org_id=org.id, active_org_id=None)
        user_id = user.id
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="viewer"))
        session.commit()

        token = create_access_token({"sub": str(user.id)})
        response = client.get(
            "/auth/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == str(user.id)
        assert body["org_id"] == str(org.id)
        assert body["role"] == "viewer"
    finally:
        session.close()
        _cleanup(user_id=user_id, org_ids=org_ids)


def test_require_org_multiple_memberships_without_active_org_returns_403() -> None:
    user_id = None
    org_ids = []
    session = SessionLocal()
    try:
        org_a = _create_org(session, "multi-a")
        org_b = _create_org(session, "multi-b")
        org_ids = [org_a.id, org_b.id]
        user = _create_user(session, org_id=org_a.id, active_org_id=None)
        user_id = user.id
        session.add(OrgMembership(user_id=user.id, org_id=org_a.id, role="admin"))
        session.add(OrgMembership(user_id=user.id, org_id=org_b.id, role="viewer"))
        session.commit()

        token = create_access_token({"sub": str(user.id)})
        response = client.get(
            "/auth/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Organization selection required"
    finally:
        session.close()
        _cleanup(user_id=user_id, org_ids=org_ids)


def test_require_org_returns_correct_auth_context() -> None:
    user_id = None
    org_ids = []
    session = SessionLocal()
    try:
        org = _create_org(session, "ctx")
        org_ids = [org.id]
        user = _create_user(session, org_id=org.id, active_org_id=org.id)
        user_id = user.id
        session.add(OrgMembership(user_id=user.id, org_id=org.id, role="owner"))
        session.commit()

        token = create_access_token(
            {"sub": str(user.id), "org_id": str(org.id), "role": "owner"}
        )
        response = client.get(
            "/auth/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body == {
            "user_id": str(user.id),
            "org_id": str(org.id),
            "role": "owner",
        }
    finally:
        session.close()
        _cleanup(user_id=user_id, org_ids=org_ids)
