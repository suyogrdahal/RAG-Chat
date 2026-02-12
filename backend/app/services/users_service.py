from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.db.models import OrgMembership, User
from app.repositories.memberships import MembershipRepository
from app.repositories.users_repository import UsersRepository
from app.schemas.users import UserCreateRequest, UserUpdateRequest


class UsersService:
    def __init__(self, repo: UsersRepository, membership_repo: MembershipRepository) -> None:
        self.repo = repo
        self.membership_repo = membership_repo

    def list(self, org_id) -> list[User]:
        return self.repo.list(org_id)

    def get_by_id(self, org_id, user_id) -> User:
        user = self.repo.get_by_id(org_id, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return user

    def create(self, org_id, payload: UserCreateRequest) -> User:
        user = User(
            org_id=org_id,
            active_org_id=org_id,
            email=str(payload.email),
            password_hash=payload.password_hash,
            role=payload.role,
            is_active=payload.is_active,
        )
        try:
            self.repo.create(org_id, user)
            self.repo.flush()
            self.membership_repo.create_membership(
                OrgMembership(user_id=user.id, org_id=org_id, role=user.role)
            )
            self.repo.commit()
            self.repo.refresh(user)
            return user
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource already exists",
            ) from exc

    def update(self, org_id, user_id, payload: UserUpdateRequest) -> User:
        user = self.repo.update(
            org_id=org_id,
            user_id=user_id,
            email=str(payload.email) if payload.email is not None else None,
            role=payload.role,
            is_active=payload.is_active,
        )
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        self.repo.commit()
        self.repo.refresh(user)
        return user

    def delete(self, org_id, user_id) -> None:
        deleted = self.repo.delete(org_id, user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        self.repo.commit()
