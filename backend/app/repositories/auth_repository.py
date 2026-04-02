from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Organization, RefreshToken, User


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_organization_by_slug(self, slug: str) -> Organization | None:
        return self.db.scalar(select(Organization).where(Organization.slug == slug))

    def get_organization_by_id(self, org_id) -> Organization | None:
        return self.db.get(Organization, org_id)

    def create_organization(self, org: Organization) -> Organization:
        self.db.add(org)
        return org

    def create_user(self, user: User) -> User:
        self.db.add(user)
        return user

    def get_user_by_org_and_email(self, org_id, email: str) -> User | None:
        return self.db.scalar(
            select(User).where(User.org_id == org_id, User.email == email)
        )

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_user_by_id(self, user_id) -> User | None:
        return self.db.get(User, user_id)

    def create_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        return refresh_token

    def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    def revoke_refresh_token(
        self, refresh_token: RefreshToken, revoked_at: datetime
    ) -> RefreshToken:
        refresh_token.revoked_at = revoked_at
        self.db.add(refresh_token)
        return refresh_token

    def set_rotated_to_token(
        self, refresh_token: RefreshToken, rotated_to_token_id
    ) -> RefreshToken:
        refresh_token.rotated_to_token_id = rotated_to_token_id
        self.db.add(refresh_token)
        return refresh_token

    def revoke_all_active_refresh_tokens_for_user(self, user_id, revoked_at: datetime) -> int:
        result = self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        return int(result.rowcount or 0)

    def update_last_login(self, user: User, last_login_at: datetime) -> User:
        user.last_login_at = last_login_at
        self.db.add(user)
        return user

    def flush(self) -> None:
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, entity) -> None:
        self.db.refresh(entity)
