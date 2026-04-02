from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import OrgMembership, Organization, RefreshToken, User, generate_widget_public_key
from app.repositories.auth_repository import AuthRepository
from app.repositories.memberships import MembershipRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    SignupResponse,
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "org"


class AuthService:
    def __init__(self, repo: AuthRepository) -> None:
        self.repo = repo
        self.membership_repo = MembershipRepository(repo.db)
        self.settings = get_settings()

    def _generate_unique_slug(self, org_name: str) -> str:
        base = _slugify(org_name)
        for _ in range(5):
            candidate = f"{base}-{uuid4().hex[:6]}"
            existing = self.repo.get_organization_by_slug(candidate)
            if existing is None:
                return candidate
        return f"{base}-{uuid4().hex}"

    def signup(self, payload: SignupRequest) -> SignupResponse:
        if payload.org_slug:
            existing = self.repo.get_organization_by_slug(payload.org_slug)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Organization slug already exists",
                )

        org_slug = payload.org_slug or self._generate_unique_slug(payload.org_name)
        org = Organization(
            name=payload.org_name,
            slug=org_slug,
            status="active",
            allowed_domains=[],
            rate_limit_per_minute=60,
            max_tokens_per_request=800,
            widget_public_key=generate_widget_public_key(),
        )
        user = User(
            org_id=org.id,
            active_org_id=org.id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="owner",
            is_active=True,
        )

        try:
            self.repo.create_organization(org)
            self.repo.flush()
            user.org_id = org.id
            self.repo.create_user(user)
            self.repo.flush()
            self.membership_repo.create_membership(
                OrgMembership(
                    user_id=user.id,
                    org_id=org.id,
                    role="owner",
                )
            )
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            message = str(exc.orig)
            if payload.org_slug and "organizations_slug_key" in message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Organization slug already exists",
                ) from exc
            if "uq_users_org_id_email" in message:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User email already exists",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource already exists",
            ) from exc

        self.repo.refresh(org)
        self.repo.refresh(user)
        return SignupResponse(org_id=org.id, user_id=user.id, message="Signup successful")

    def _invalid_refresh_token_error(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    def _issue_refresh_token(
        self,
        user_id,
        now: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, RefreshToken]:
        refresh_token_value = create_refresh_token_value()
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(refresh_token_value),
            created_at=now,
            expires_at=now + timedelta(days=self.settings.refresh_ttl_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.repo.create_refresh_token(refresh_token)
        return refresh_token_value, refresh_token

    def login(self, payload: LoginRequest) -> LoginResponse:
        # Look up user by email first (single source of truth for password verification)
        user = self.repo.get_user_by_email(payload.email)
        if user is None or user.password_hash is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials or user not found",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
            )
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials password",
            )

        # Resolve organization context after password validation
        org = None
        if payload.org_id is not None:
            org = self.repo.get_organization_by_id(payload.org_id)
        elif payload.org_slug:
            org = self.repo.get_organization_by_slug(payload.org_slug)
        else:
            # fallback to user's active_org_id
            if user.org_id:
                org = self.repo.get_organization_by_id(user.org_id)

        if org is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No organization found for user",
            )

        now = datetime.now(timezone.utc)
        self.repo.update_last_login(user, now)
        refresh_token_value, _ = self._issue_refresh_token(user.id, now)
        self.repo.commit()
        self.repo.refresh(user)

        memberships = self.membership_repo.list_user_memberships(user.id)
        memberships_by_org = {membership.org_id: membership for membership in memberships}

        selected_membership = None
        if payload.org_id is not None:
            selected_membership = memberships_by_org.get(payload.org_id)
        elif payload.org_slug:
            selected_membership = memberships_by_org.get(org.id)

        if selected_membership is None and user.active_org_id is not None:
            selected_membership = memberships_by_org.get(user.active_org_id)
        if selected_membership is None and len(memberships) == 1:
            selected_membership = memberships[0]

        token_payload = {"sub": user.id}
        if selected_membership is not None:
            token_payload["org_id"] = selected_membership.org_id
            token_payload["role"] = selected_membership.role

        access_token = create_access_token(token_payload)
        return LoginResponse(
            org_id=org.id,
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token_value,
        )

    def rotate_refresh_token(self, payload: RefreshRequest) -> RefreshResponse:
        now = datetime.now(timezone.utc)
        old_token = self.repo.get_refresh_token_by_hash(
            hash_refresh_token(payload.refresh_token)
        )
        if old_token is None:
            raise self._invalid_refresh_token_error()

        if old_token.revoked_at is not None:
            if old_token.rotated_to_token_id is not None:
                self.repo.revoke_all_active_refresh_tokens_for_user(old_token.user_id, now)
                self.repo.commit()
            raise self._invalid_refresh_token_error()

        if old_token.expires_at <= now:
            self.repo.revoke_refresh_token(old_token, now)
            self.repo.commit()
            raise self._invalid_refresh_token_error()

        user = self.repo.get_user_by_id(old_token.user_id)
        if user is None or not user.is_active:
            self.repo.revoke_refresh_token(old_token, now)
            self.repo.commit()
            raise self._invalid_refresh_token_error()

        new_refresh_token_value, new_refresh_token = self._issue_refresh_token(
            old_token.user_id,
            now,
            user_agent=old_token.user_agent,
            ip_address=old_token.ip_address,
        )
        self.repo.flush()
        self.repo.revoke_refresh_token(old_token, now)
        self.repo.set_rotated_to_token(old_token, new_refresh_token.id)
        self.repo.commit()

        memberships = self.membership_repo.list_user_memberships(user.id)
        memberships_by_org = {membership.org_id: membership for membership in memberships}
        selected_membership = None
        if user.active_org_id is not None:
            selected_membership = memberships_by_org.get(user.active_org_id)
        if selected_membership is None and len(memberships) == 1:
            selected_membership = memberships[0]

        token_payload = {"sub": user.id}
        if selected_membership is not None:
            token_payload["org_id"] = selected_membership.org_id
            token_payload["role"] = selected_membership.role

        access_token = create_access_token(token_payload)
        return RefreshResponse(
            access_token=access_token,
            refresh_token=new_refresh_token_value,
        )
