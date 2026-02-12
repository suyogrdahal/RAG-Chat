from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.repositories.memberships import MembershipRepository
from app.schemas.auth_context import AuthContext

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUserContext:
    user: User
    token_org_id: UUID | None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _parse_uuid(value, required: bool) -> UUID | None:
    if value is None:
        if required:
            raise _unauthorized()
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise _unauthorized()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUserContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise _unauthorized()

    token_type = payload.get("type")
    if token_type != "access":
        raise _unauthorized()
    if "exp" not in payload or "iat" not in payload:
        raise _unauthorized()
    if not isinstance(payload.get("iat"), int):
        raise _unauthorized()

    user_id = _parse_uuid(payload.get("sub"), required=True)
    token_org_id = _parse_uuid(payload.get("org_id"), required=False)

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    request.state.user_id = str(user.id)
    return CurrentUserContext(user=user, token_org_id=token_org_id)


def require_org(
    request: Request,
    current_user: CurrentUserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthContext:
    repo = MembershipRepository(db)
    memberships = repo.list_user_memberships(current_user.user.id)
    by_org = {m.org_id: m for m in memberships}

    org_id: UUID | None = None
    membership = None

    if current_user.token_org_id is not None:
        membership = by_org.get(current_user.token_org_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        org_id = current_user.token_org_id
    elif current_user.user.active_org_id is not None:
        membership = by_org.get(current_user.user.active_org_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        org_id = current_user.user.active_org_id
    elif len(memberships) == 1:
        membership = memberships[0]
        org_id = membership.org_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization selection required",
        )

    ctx = AuthContext(
        user_id=current_user.user.id,
        org_id=org_id,
        role=membership.role,
    )
    request.state.user_id = str(ctx.user_id)
    request.state.org_id = str(ctx.org_id)
    return ctx


def require_role(min_role: str) -> Callable[[AuthContext], AuthContext]:
    order = {"viewer": 10, "editor": 20, "admin": 30, "owner": 40}

    def _checker(context: AuthContext = Depends(require_org)) -> AuthContext:
        current = order.get(context.role, -1)
        expected = order.get(min_role, 999)
        if current < expected:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return context

    return _checker
