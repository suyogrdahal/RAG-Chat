from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.repositories.scoped import scoped_get


class UsersRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, org_id) -> list[User]:
        return list(self.db.scalars(select(User).where(User.org_id == org_id)).all())

    def get_by_id(self, org_id, user_id) -> User | None:
        return scoped_get(self.db, User, org_id, user_id)

    def create(self, org_id, user: User) -> User:
        user.org_id = org_id
        user.active_org_id = org_id
        self.db.add(user)
        return user

    def update(self, org_id, user_id, email: str | None = None, role: str | None = None, is_active: bool | None = None) -> User | None:
        user = self.get_by_id(org_id, user_id)
        if user is None:
            return None
        if email is not None:
            user.email = email
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        self.db.add(user)
        return user

    def delete(self, org_id, user_id) -> bool:
        user = self.get_by_id(org_id, user_id)
        if user is None:
            return False
        self.db.delete(user)
        return True

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, entity) -> None:
        self.db.refresh(entity)
