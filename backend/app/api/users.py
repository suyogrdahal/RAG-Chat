from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps.auth import require_org, require_role
from app.db.session import get_db
from app.repositories.memberships import MembershipRepository
from app.repositories.users_repository import UsersRepository
from app.schemas.auth_context import AuthContext
from app.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest
from app.services.users_service import UsersService

router = APIRouter(prefix="/users", tags=["users"])


def get_users_service(db: Session = Depends(get_db)) -> UsersService:
    return UsersService(UsersRepository(db), MembershipRepository(db))


@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
def list_users(
    context: AuthContext = Depends(require_org),
    service: UsersService = Depends(get_users_service),
) -> list[UserResponse]:
    users = service.list(context.org_id)
    return [
        UserResponse(
            id=u.id,
            org_id=u.org_id,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
        )
        for u in users
    ]


@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(
    user_id: UUID,
    context: AuthContext = Depends(require_org),
    service: UsersService = Depends(get_users_service),
) -> UserResponse:
    user = service.get_by_id(context.org_id, user_id)
    return UserResponse(
        id=user.id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
def create_user(
    payload: UserCreateRequest,
    context: AuthContext = Depends(require_org),
    service: UsersService = Depends(get_users_service),
) -> UserResponse:
    user = service.create(context.org_id, payload)
    return UserResponse(
        id=user.id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role("admin"))],
)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    context: AuthContext = Depends(require_org),
    service: UsersService = Depends(get_users_service),
) -> UserResponse:
    user = service.update(context.org_id, user_id, payload)
    return UserResponse(
        id=user.id,
        org_id=user.org_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_role("admin"))],
)
def delete_user(
    user_id: UUID,
    context: AuthContext = Depends(require_org),
    service: UsersService = Depends(get_users_service),
) -> Response:
    service.delete(context.org_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
