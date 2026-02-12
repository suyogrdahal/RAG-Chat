from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import OrgMembership, Organization, User
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _cleanup(org_ids: list | None = None, user_ids: list | None = None) -> None:
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


def _setup_two_orgs():
    session = SessionLocal()
    try:
        org_a = Organization(name="Org A", slug=f"orga-{uuid4().hex[:8]}")
        org_b = Organization(name="Org B", slug=f"orgb-{uuid4().hex[:8]}")
        session.add(org_a)
        session.add(org_b)
        session.flush()

        user_a = User(
            org_id=org_a.id,
            active_org_id=org_a.id,
            email=f"admin-a-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
            role="admin",
            is_active=True,
        )
        user_b = User(
            org_id=org_b.id,
            active_org_id=org_b.id,
            email=f"admin-b-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
            role="admin",
            is_active=True,
        )
        session.add(user_a)
        session.add(user_b)
        session.flush()

        session.add(OrgMembership(user_id=user_a.id, org_id=org_a.id, role="admin"))
        session.add(OrgMembership(user_id=user_b.id, org_id=org_b.id, role="admin"))

        member_a = User(
            org_id=org_a.id,
            active_org_id=org_a.id,
            email=f"user-a-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
            role="viewer",
            is_active=True,
        )
        member_b = User(
            org_id=org_b.id,
            active_org_id=org_b.id,
            email=f"user-b-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("TestPass123!"),
            role="viewer",
            is_active=True,
        )
        session.add(member_a)
        session.add(member_b)
        session.flush()
        session.add(OrgMembership(user_id=member_a.id, org_id=org_a.id, role="viewer"))
        session.add(OrgMembership(user_id=member_b.id, org_id=org_b.id, role="viewer"))

        session.commit()
        return {
            "org_a_id": org_a.id,
            "org_b_id": org_b.id,
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
            "member_a_id": member_a.id,
            "member_b_id": member_b.id,
        }
    finally:
        session.close()


def _auth_headers(user_id, org_id) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "org_id": str(org_id)})
    return {"Authorization": f"Bearer {token}"}


def test_user_a_list_contains_only_org_a_users() -> None:
    data = _setup_two_orgs()
    try:
        response = client.get("/users", headers=_auth_headers(data["user_a_id"], data["org_a_id"]))
        assert response.status_code == 200, response.text
        payload = response.json()
        assert all(item["org_id"] == str(data["org_a_id"]) for item in payload)
        ids = {item["id"] for item in payload}
        assert str(data["member_a_id"]) in ids
        assert str(data["member_b_id"]) not in ids
    finally:
        _cleanup(
            org_ids=[data["org_a_id"], data["org_b_id"]],
            user_ids=[data["user_a_id"], data["user_b_id"], data["member_a_id"], data["member_b_id"]],
        )


def test_user_a_cannot_get_org_b_user_by_id_returns_404() -> None:
    data = _setup_two_orgs()
    try:
        response = client.get(
            f"/users/{data['member_b_id']}",
            headers=_auth_headers(data["user_a_id"], data["org_a_id"]),
        )
        assert response.status_code == 404, response.text
    finally:
        _cleanup(
            org_ids=[data["org_a_id"], data["org_b_id"]],
            user_ids=[data["user_a_id"], data["user_b_id"], data["member_a_id"], data["member_b_id"]],
        )


def test_user_a_cannot_update_org_b_user_by_id_returns_404() -> None:
    data = _setup_two_orgs()
    try:
        response = client.patch(
            f"/users/{data['member_b_id']}",
            headers=_auth_headers(data["user_a_id"], data["org_a_id"]),
            json={"role": "editor"},
        )
        assert response.status_code == 404, response.text
    finally:
        _cleanup(
            org_ids=[data["org_a_id"], data["org_b_id"]],
            user_ids=[data["user_a_id"], data["user_b_id"], data["member_a_id"], data["member_b_id"]],
        )


def test_user_a_cannot_delete_org_b_user_by_id_returns_404() -> None:
    data = _setup_two_orgs()
    try:
        response = client.delete(
            f"/users/{data['member_b_id']}",
            headers=_auth_headers(data["user_a_id"], data["org_a_id"]),
        )
        assert response.status_code == 404, response.text
    finally:
        _cleanup(
            org_ids=[data["org_a_id"], data["org_b_id"]],
            user_ids=[data["user_a_id"], data["user_b_id"], data["member_a_id"], data["member_b_id"]],
        )


def test_user_create_ignores_body_org_id_uses_context_org_id() -> None:
    data = _setup_two_orgs()
    created_id = None
    try:
        response = client.post(
            "/users",
            headers=_auth_headers(data["user_a_id"], data["org_a_id"]),
            json={
                "email": f"new-{uuid4().hex[:8]}@example.com",
                "password_hash": "hash",
                "role": "viewer",
                "is_active": True,
                "org_id": str(data["org_b_id"]),
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        created_id = UUID(body["id"])
        assert body["org_id"] == str(data["org_a_id"])
    finally:
        if created_id is not None:
            session = SessionLocal()
            try:
                created = session.get(User, created_id)
                if created is not None:
                    session.delete(created)
                    session.commit()
            finally:
                session.close()
        _cleanup(
            org_ids=[data["org_a_id"], data["org_b_id"]],
            user_ids=[data["user_a_id"], data["user_b_id"], data["member_a_id"], data["member_b_id"]],
        )
