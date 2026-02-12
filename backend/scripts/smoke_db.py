import sys
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import Organization, User
from app.db.session import SessionLocal


def main() -> int:
    session = SessionLocal()
    try:
        try:
            session.execute(text("SELECT 1"))
        except Exception as exc:
            print(f"DB connection failed: {exc}")
            return 1

        org = Organization(name="Smoke Org", slug=f"smoke-org-{uuid4().hex[:8]}")
        session.add(org)
        try:
            session.commit()
            session.refresh(org)
        except Exception as exc:
            session.rollback()
            print(f"Failed to create organization: {exc}")
            return 1

        user = User(
            org_id=org.id,
            email="smoke@example.com",
            role="admin",
            password_hash=None,
        )
        session.add(user)
        try:
            session.commit()
            session.refresh(user)
        except Exception as exc:
            session.rollback()
            print(f"Failed to create user: {exc}")
            return 1

        org_read = session.get(Organization, org.id)
        user_read = session.get(User, user.id)
        if org_read is None or user_read is None:
            print("Failed to read back organization or user")
            return 1

        print(f"org: id={org_read.id} name={org_read.name} slug={org_read.slug}")
        print(
            "user: "
            f"id={user_read.id} org_id={user_read.org_id} "
            f"email={user_read.email} role={user_read.role}"
        )

        duplicate = User(
            org_id=org.id,
            email="smoke@example.com",
            role="admin",
            password_hash=None,
        )
        session.add(duplicate)
        try:
            session.commit()
            print("unique constraint NOT enforced")
            return 1
        except IntegrityError:
            session.rollback()
            print("unique constraint enforced")
        except Exception as exc:
            session.rollback()
            print(f"Unexpected error on unique constraint check: {exc}")
            return 1

        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
